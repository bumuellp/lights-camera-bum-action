#!/usr/bin/env python3
"""Clean up orphaned and stale container package versions from GHCR."""

from datetime import datetime, timezone
import json
import os
import re
import subprocess
import sys


def parse_packages(raw_packages: str) -> list[str]:
    """Parse comma-separated or JSON list of package names."""
    raw_packages = raw_packages.strip()
    if not raw_packages or raw_packages == "auto":
        # Auto-discover from images directory if present
        if os.path.isdir("images"):
            return [
                d for d in sorted(os.listdir("images"))
                if os.path.isfile(os.path.join("images", d, "Dockerfile"))
            ]
        return []

    if raw_packages.startswith("["):
        parsed = json.loads(raw_packages)
        result = []
        for item in parsed:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and "name" in item:
                result.append(item["name"])
        return result

    return [p.strip() for p in raw_packages.replace(",", " ").split() if p.strip()]


def is_semver_release(tags: list[str]) -> bool:
    """Check if any tag matches exact SemVer release (e.g. v1.0.0, 1.2.3)."""
    pattern = re.compile(r"^v?[0-9]+\.[0-9]+\.[0-9]+$")
    return any(pattern.match(t) for t in tags)


def is_active_floating(tags: list[str]) -> bool:
    """Check if tag contains floating release branches (:latest, :v1, :v2)."""
    floating_pattern = re.compile(r"^(latest|v?[0-9]+|v?[0-9]+\.[0-9]+)$")
    return any(floating_pattern.match(t) for t in tags)


def cleanup_package_versions(
    package_name: str,
    owner: str,
    token: str,
    keep_sha_count: int = 5,
    dry_run: bool = False,
) -> dict:
    """Clean up untagged and stale commit SHA versions for a package."""
    headers = ["-H", "Accept: application/vnd.github+json"]
    if token:
        headers.extend(["-H", f"Authorization: Bearer {token}"])

    endpoint = f"/user/packages/container/{package_name}/versions?per_page=100"
    cmd = ["gh", "api", endpoint, "--paginate"] + headers

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            print(f"[{package_name}] Warning: Failed to fetch versions: {res.stderr.strip()}", file=sys.stderr)
            return {"kept": 0, "deleted": 0}
        versions = json.loads(res.stdout)
    except Exception as e:
        print(f"[{package_name}] Error: {e}", file=sys.stderr)
        return {"kept": 0, "deleted": 0}

    # Sort versions newest to oldest
    versions.sort(key=lambda v: v.get("created_at", ""), reverse=True)

    kept_sha_count = 0
    kept = 0
    deleted = 0

    print(f"--- Processing {package_name} ({len(versions)} total versions) ---")

    for v in versions:
        vid = v["id"]
        tags = v.get("metadata", {}).get("container", {}).get("tags", [])
        created_at = v.get("created_at", "")

        # 1. ALWAYS PRESERVE SemVer Release checkpoints (e.g. v1.0.0)
        if is_semver_release(tags):
            print(f"  [KEEP-SEMVER] ID {vid} ({created_at}) tags: {tags}")
            kept += 1
            continue

        # 2. ALWAYS PRESERVE Active Floating tags (:latest, :v1)
        if is_active_floating(tags):
            print(f"  [KEEP-ACTIVE] ID {vid} ({created_at}) tags: {tags}")
            kept += 1
            continue

        # 3. Retain the most recent N commit SHA versions
        if tags and kept_sha_count < keep_sha_count:
            print(f"  [KEEP-RECENT-SHA] ID {vid} ({created_at}) tags: {tags} ({kept_sha_count + 1}/{keep_sha_count})")
            kept_sha_count += 1
            kept += 1
            continue

        # 4. Untagged or older SHA version: DELETE
        action = "[DRY-RUN DELETE]" if dry_run else "[DELETE]"
        print(f"  {action} ID {vid} ({created_at}) tags: {tags}")

        if not dry_run:
            del_cmd = ["gh", "api", "-X", "DELETE", f"/user/packages/container/{package_name}/versions/{vid}"] + headers
            del_res = subprocess.run(del_cmd, capture_output=True, text=True, check=False)
            if del_res.returncode == 0:
                deleted += 1
            else:
                print(f"    -> Delete failed: {del_res.stderr.strip()}", file=sys.stderr)
        else:
            deleted += 1

    return {"kept": kept, "deleted": deleted}


def main() -> None:
    raw_packages = os.environ.get("INPUT_PACKAGE_NAMES", "auto")
    owner = os.environ.get("INPUT_REPOSITORY_OWNER", os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    token = os.environ.get("INPUT_TOKEN", os.environ.get("GITHUB_TOKEN", ""))
    keep_sha_count = int(os.environ.get("INPUT_KEEP_SHA_COUNT", "5"))
    dry_run = os.environ.get("INPUT_DRY_RUN", "false").lower() in ("true", "1")

    packages = parse_packages(raw_packages)
    if not packages:
        print("No packages found or specified to clean.")
        return

    total_kept = 0
    total_deleted = 0

    for pkg in packages:
        stats = cleanup_package_versions(
            package_name=pkg,
            owner=owner,
            token=token,
            keep_sha_count=keep_sha_count,
            dry_run=dry_run,
        )
        total_kept += stats["kept"]
        total_deleted += stats["deleted"]

    print(f"\nCleanup complete. Kept: {total_kept}, Deleted: {total_deleted}")


if __name__ == "__main__":
    main()
