#!/usr/bin/env python3
"""Setup and run Ansible collection builds, dependency installs, and syntax checks."""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_ANSIBLE_CORE_VERSION = "2.21.4"
DEFAULT_ANSIBLE_LINT_VERSION = "26.8.0"
DEFAULT_YAMLLINT_VERSION = "1.37.1"
DEFAULT_PLAYBOOKS_GLOB = "playbooks/*.yml tests/*playbook*.yml"
DEFAULT_INVENTORY = "tests/inventory.ini"
DEFAULT_GALAXY_FILE = "galaxy.yml"
DEFAULT_REQUIREMENTS_FILE = "requirements.yml"


def _env_or_default(name: str, default: str) -> str:
    """Return environment variable value, keeping explicit empty strings."""
    return os.environ[name] if name in os.environ else default


def _venv_dir() -> Path:
    """Resolve the isolated Ansible virtualenv path."""
    raw = os.environ.get("ANSIBLE_VENV_DIR", "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".local" / "share" / "ansible-test-venv"


def _run_cmd(cmd: list[str], env: dict[str, str] | None = None) -> int:
    """Run a subprocess without raising, returning its exit code."""
    sys.stdout.flush()
    sys.stderr.flush()
    return subprocess.run(cmd, env=env, check=False).returncode


def cmd_setup() -> int:
    """Ensure the isolated ansible-core (and optional lint) venv matches spec."""
    venv_dir = _venv_dir()
    run_lint = os.environ.get("RUN_LINT", "false").strip().lower() == "true"
    marker_file = venv_dir / ".installed-spec"

    core_ver = os.environ.get("ANSIBLE_CORE_VERSION") or DEFAULT_ANSIBLE_CORE_VERSION
    lint_ver = os.environ.get("ANSIBLE_LINT_VERSION") or DEFAULT_ANSIBLE_LINT_VERSION
    yaml_ver = os.environ.get("YAMLLINT_VERSION") or DEFAULT_YAMLLINT_VERSION

    pkgs = [f"ansible-core=={core_ver}"]
    required_bins = ["python", "ansible-playbook", "ansible-galaxy"]
    if run_lint:
        pkgs.extend([f"ansible-lint=={lint_ver}", f"yamllint=={yaml_ver}"])
        required_bins.extend(["ansible-lint", "yamllint"])

    spec = f"py{sys.version_info.major}.{sys.version_info.minor} {' '.join(pkgs)}"
    bins_ready = all(
        (venv_dir / "bin" / name).is_file() and os.access(venv_dir / "bin" / name, os.X_OK)
        for name in required_bins
    )
    if bins_ready and marker_file.is_file() and marker_file.read_text(encoding="utf-8") == spec:
        print(f"Ansible environment already installed: {spec}")
        return 0

    print(f"Installing {spec} into {venv_dir}...")
    rc = _run_cmd([sys.executable, "-m", "venv", "--clear", str(venv_dir)])
    if rc != 0:
        return rc

    uv_bin = shutil.which("uv")
    if uv_bin:
        install_cmd = [
            uv_bin,
            "pip",
            "install",
            "--python",
            str(venv_dir / "bin" / "python"),
            "--quiet",
            *pkgs,
        ]
    else:
        install_cmd = [
            str(venv_dir / "bin" / "pip"),
            "install",
            "--quiet",
            "--no-cache-dir",
            *pkgs,
        ]

    rc = _run_cmd(install_cmd)
    if rc != 0:
        return rc

    marker_file.write_text(spec, encoding="utf-8")
    return 0


def _install_galaxy_dependencies(
    galaxy_file: Path, tmp_dir: Path, collections_dir: Path, env: dict[str, str]
) -> int:
    """Install dependencies declared in galaxy.yml into the cached dir."""
    import yaml

    data = yaml.safe_load(galaxy_file.read_text(encoding="utf-8")) or {}
    deps = data.get("dependencies") or {}
    if not deps:
        return 0
    if not isinstance(deps, dict):
        print(
            f"ERROR: dependencies in {galaxy_file} must be a mapping",
            file=sys.stderr,
        )
        return 1

    deps_req = tmp_dir / "galaxy-deps.yml"
    items = [
        {"name": name, "version": str(ver)}
        if ver is not None and str(ver).strip()
        else {"name": name}
        for name, ver in deps.items()
    ]
    deps_req.write_text(yaml.safe_dump({"collections": items}), encoding="utf-8")
    print(f"=== Installing collection dependencies from {galaxy_file} ===")
    return _run_cmd(
        [
            "ansible-galaxy",
            "collection",
            "install",
            "--upgrade",
            "-r",
            str(deps_req),
            "-p",
            str(collections_dir),
        ],
        env=env,
    )


def _build_local_collection(
    galaxy_file: Path, tmp_dir: Path, collections_dir: Path, env: dict[str, str]
) -> tuple[int, Path | None]:
    """Build local collection and install it into an uncached temp directory."""
    rc = _install_galaxy_dependencies(galaxy_file, tmp_dir, collections_dir, env)
    if rc != 0:
        return rc, None

    galaxy_dir = str(galaxy_file.parent) or "."
    print(f"=== Building collection from {galaxy_dir} ===")
    rc = _run_cmd(
        [
            "ansible-galaxy",
            "collection",
            "build",
            "--force",
            "--output-path",
            str(tmp_dir),
            galaxy_dir,
        ],
        env=env,
    )
    if rc != 0:
        return rc, None

    tarballs = sorted(tmp_dir.glob("*.tar.gz"))
    if not tarballs:
        print("ERROR: collection build produced no tarball", file=sys.stderr)
        return 1, None

    local_dir = tmp_dir / "collections"
    local_dir.mkdir(parents=True, exist_ok=True)
    rc = _run_cmd(
        [
            "ansible-galaxy",
            "collection",
            "install",
            "--no-deps",
            "--force",
            str(tarballs[0]),
            "-p",
            str(local_dir),
        ],
        env=env,
    )
    return rc, local_dir


def _discover_playbooks(playbooks_glob: str) -> list[str]:
    """Expand space/newline-separated glob patterns while preserving order."""
    seen: set[str] = set()
    playbooks: list[str] = []
    for pattern in playbooks_glob.split():
        for match in sorted(glob.glob(pattern, recursive=True)):
            if Path(match).is_file() and match not in seen:
                seen.add(match)
                playbooks.append(match)
    return playbooks


def _compose_collections_path(local_dir: Path | None, collections_dir: Path, existing: str) -> str:
    """Build colon-separated ANSIBLE_COLLECTIONS_PATH without empty entries."""
    parts: list[str] = []
    if local_dir is not None:
        parts.append(str(local_dir))
    parts.append(str(collections_dir))
    if existing:
        parts.append(existing)
    return os.pathsep.join(parts)


def cmd_run() -> int:
    """Build/install Ansible collections, optionally lint, and syntax-check playbooks."""
    playbooks_glob = os.environ.get("PLAYBOOKS_GLOB") or DEFAULT_PLAYBOOKS_GLOB
    inventory = _env_or_default("INVENTORY", DEFAULT_INVENTORY)
    galaxy_raw = _env_or_default("GALAXY_FILE", DEFAULT_GALAXY_FILE)
    requirements_raw = _env_or_default("REQUIREMENTS_FILE", DEFAULT_REQUIREMENTS_FILE)
    run_lint = os.environ.get("RUN_LINT", "false").strip().lower() == "true"

    env = os.environ.copy()
    venv_bin = _venv_dir() / "bin"
    if venv_bin.is_dir():
        existing_path = env.get("PATH", "")
        env["PATH"] = f"{venv_bin}{os.pathsep}{existing_path}" if existing_path else str(venv_bin)

    collections_raw = env.get("ANSIBLE_TEST_COLLECTIONS_DIR", "").strip()
    collections_dir = (
        Path(collections_raw) if collections_raw else Path.home() / ".ansible" / "collections"
    )
    collections_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        local_dir: Path | None = None

        if galaxy_raw and Path(galaxy_raw).is_file():
            rc, local_dir = _build_local_collection(Path(galaxy_raw), tmp_dir, collections_dir, env)
            if rc != 0:
                return rc

        if requirements_raw and Path(requirements_raw).is_file():
            print(f"=== Installing collections from {requirements_raw} ===")
            rc = _run_cmd(
                [
                    "ansible-galaxy",
                    "collection",
                    "install",
                    "--upgrade",
                    "-r",
                    requirements_raw,
                    "-p",
                    str(collections_dir),
                ],
                env=env,
            )
            if rc != 0:
                return rc

        env["ANSIBLE_COLLECTIONS_PATH"] = _compose_collections_path(
            local_dir, collections_dir, env.get("ANSIBLE_COLLECTIONS_PATH", "")
        )

        if run_lint:
            print("=== Running yamllint ===")
            rc = _run_cmd(["yamllint", "."], env=env)
            if rc != 0:
                return rc
            print("=== Running ansible-lint ===")
            rc = _run_cmd(["ansible-lint"], env=env)
            if rc != 0:
                return rc

        inv_args: list[str] = []
        if inventory:
            if not Path(inventory).is_file():
                print(f"ERROR: Inventory file not found: {inventory}", file=sys.stderr)
                return 1
            inv_args = ["-i", inventory]

        playbooks = _discover_playbooks(playbooks_glob)
        if not playbooks:
            print(f"ERROR: No playbooks found matching: {playbooks_glob}", file=sys.stderr)
            return 1

        for pb in playbooks:
            print(f"=== Syntax-checking {pb} ===")
            rc = _run_cmd(["ansible-playbook", *inv_args, pb, "--syntax-check"], env=env)
            if rc != 0:
                return rc

    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse CLI subcommands and dispatch to setup or run."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description="Ansible collection test helper")
    parser.add_argument("command", choices=["setup", "run"])
    args = parser.parse_args(argv)
    if args.command == "setup":
        return cmd_setup()
    return cmd_run()


if __name__ == "__main__":
    raise SystemExit(main())
