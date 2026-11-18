#!/usr/bin/env python3
"""Discover mise tool specifications generically from pre-commit configs and hook repos."""

from __future__ import annotations

import datetime
import hashlib
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

import yaml

TAG_PATTERN = re.compile(r"\[(?:tools|requires)\s*:\s*([^\]]+)\]", re.IGNORECASE)
MISE_FILES = ("mise.toml", ".mise.toml", ".tool-versions", ".mise/config.toml")


def _split_specs(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        items: list[str] = []
        for entry in raw:
            items.extend(_split_specs(entry))
        return items
    return [tok.strip() for tok in re.split(r"[\s,]+", str(raw).strip()) if tok.strip()]


def _extract_from_description(description: str | None) -> list[str]:
    if not description:
        return []
    specs: list[str] = []
    for match in TAG_PATTERN.finditer(description):
        specs.extend(_split_specs(match.group(1)))
    return specs


def _resolve_repo_dirs(pre_commit_home: Path) -> dict[tuple[str, str], Path]:
    db_path = pre_commit_home / "db.db"
    if not db_path.is_file():
        return {}
    mapping: dict[tuple[str, str], Path] = {}
    with sqlite3.connect(db_path) as conn:
        for repo, ref, path in conn.execute("SELECT repo, ref, path FROM repos"):
            repo_path = Path(path)
            mapping[(repo.rstrip("/"), ref)] = repo_path
            mapping[(repo, ref)] = repo_path
    return mapping


def _collect_from_tools_manifest(repo_dir: Path, enabled_ids: set[str]) -> list[str]:
    specs: list[str] = []
    for filename in (".pre-commit-tools.yaml", ".pre-commit-tools.yml"):
        manifest_path = repo_dir / filename
        if not manifest_path.is_file():
            continue
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            continue
        for key in ("_default", *sorted(enabled_ids)):
            if key in data:
                specs.extend(_split_specs(data[key]))
        break
    return specs


def _collect_from_hooks_manifest(repo_dir: Path, enabled_ids: set[str]) -> list[str]:
    hooks_file = repo_dir / ".pre-commit-hooks.yaml"
    if not hooks_file.is_file():
        return []
    data = yaml.safe_load(hooks_file.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        return []
    specs: list[str] = []
    for hook in data:
        if isinstance(hook, dict) and hook.get("id") in enabled_ids:
            specs.extend(_extract_from_description(hook.get("description")))
    return specs


def discover_tools(
    workspace: Path,
    pre_commit_home: Path,
    extra_tools_raw: str = "",
) -> dict[str, str]:
    """Collect deduplicated tool specs and cache metadata for a workspace."""
    specs: list[str] = []
    config_path = workspace / ".pre-commit-config.yaml"
    repo_dirs = _resolve_repo_dirs(pre_commit_home)

    if config_path.is_file():
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        for repo_entry in config.get("repos") or []:
            if not isinstance(repo_entry, dict):
                continue
            hooks = repo_entry.get("hooks") or []
            enabled_ids = {h["id"] for h in hooks if isinstance(h, dict) and "id" in h}
            repo_url = str(repo_entry.get("repo", ""))

            if repo_url == "local":
                for hook in hooks:
                    if isinstance(hook, dict):
                        specs.extend(_extract_from_description(hook.get("description")))
                specs.extend(_collect_from_tools_manifest(workspace, enabled_ids))
            else:
                rev = str(repo_entry.get("rev", ""))
                repo_dir = repo_dirs.get((repo_url, rev)) or repo_dirs.get(
                    (repo_url.rstrip("/"), rev)
                )
                if repo_dir and repo_dir.is_dir():
                    specs.extend(_collect_from_tools_manifest(repo_dir, enabled_ids))
                    specs.extend(_collect_from_hooks_manifest(repo_dir, enabled_ids))

    specs.extend(_split_specs(extra_tools_raw))
    unique_tools = sorted(set(specs))

    mise_config_contents: list[bytes] = []
    for rel in MISE_FILES:
        candidate = workspace / rel
        if candidate.is_file():
            mise_config_contents.append(candidate.read_bytes())

    has_mise_config = bool(mise_config_contents)
    needs_mise = bool(unique_tools) or has_mise_config
    has_trivy = any("trivy" in tool.lower() for tool in unique_tools) or any(
        b"trivy" in blob.lower() for blob in mise_config_contents
    )

    hasher = hashlib.sha256()
    hasher.update("\n".join(unique_tools).encode("utf-8"))
    for blob in mise_config_contents:
        hasher.update(b"\0")
        hasher.update(blob)

    now_utc = datetime.datetime.now(datetime.UTC)
    return {
        "tools": " ".join(unique_tools),
        "needs_mise": "true" if needs_mise else "false",
        "has_trivy": "true" if has_trivy else "false",
        "tools_hash": hasher.hexdigest()[:16],
        "trivy_db_week": now_utc.strftime("%Y-%W"),
    }


def main() -> None:
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    pre_commit_home = Path(
        os.environ.get("PRE_COMMIT_HOME", str(Path.home() / ".cache" / "pre-commit"))
    )
    extra_tools = os.environ.get("EXTRA_TOOLS", "")
    outputs = discover_tools(workspace, pre_commit_home, extra_tools)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            for key, value in outputs.items():
                fh.write(f"{key}={value}\n")

    print(
        f"Discovered tools: {outputs['tools'] or 'none'} "
        f"(needs_mise={outputs['needs_mise']}, has_trivy={outputs['has_trivy']})"
    )


if __name__ == "__main__":
    main()
