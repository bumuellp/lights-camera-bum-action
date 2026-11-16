"""Unit tests for setup-rust action and helper scripts."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "setup-rust"
ACTION_FILE = ACTION_DIR / "action.yml"
RUN_CHECKS_SH = ACTION_DIR / "run_checks.sh"
INSTALL_WORKER_BUILD_SH = ACTION_DIR / "install_worker_build.sh"


def test_action_manifest_valid_and_has_no_inline_bash():
    assert ACTION_FILE.is_file()
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Setup Rust Toolchain"
    for key in ("run-fmt", "run-clippy", "clippy-args", "run-test", "test-args"):
        assert key in data["inputs"]

    for step in data["runs"]["steps"]:
        if "run" in step:
            assert "GITHUB_ACTION_PATH" in step["run"], (
                "setup-rust steps must delegate to scripts rather than inline bash"
            )


def test_scripts_are_executable():
    for script in (RUN_CHECKS_SH, INSTALL_WORKER_BUILD_SH):
        assert script.is_file()
        if not os.access(script, os.X_OK):
            script.chmod(0o755)
        assert os.access(script, os.X_OK)


def test_run_checks_executes_fmt_clippy_test_for_multiple_workspaces(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    cargo_log = tmp_path / "cargo.log"

    mock_cargo = mock_bin / "cargo"
    mock_cargo.write_text(f"""#!/usr/bin/env bash
echo "cargo $*" >> "{cargo_log}"
exit 0
""")
    mock_cargo.chmod(0o755)

    for crate in ("crate-a", "crate-b"):
        d = tmp_path / crate
        d.mkdir()
        (d / "Cargo.toml").write_text("[package]\nname = 'test'\nversion = '0.1.0'\n")

    env = {
        "PATH": f"{mock_bin}:/usr/bin:/bin",
        "WORKSPACES": "crate-a crate-b/",
        "RUN_FMT": "true",
        "RUN_CLIPPY": "true",
        "CLIPPY_ARGS": "--all-targets -- -D warnings",
        "RUN_TEST": "true",
        "TEST_ARGS": "",
    }

    res = subprocess.run(
        ["bash", str(RUN_CHECKS_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res.returncode == 0, res.stderr

    calls = cargo_log.read_text().splitlines()
    assert calls == [
        "cargo fmt --manifest-path crate-a/Cargo.toml --check",
        "cargo fmt --manifest-path crate-b/Cargo.toml --check",
        "cargo clippy --manifest-path crate-a/Cargo.toml --all-targets -- -D warnings",
        "cargo clippy --manifest-path crate-b/Cargo.toml --all-targets -- -D warnings",
        "cargo test --manifest-path crate-a/Cargo.toml",
        "cargo test --manifest-path crate-b/Cargo.toml",
    ]


def test_run_checks_fails_on_missing_manifest(tmp_path):
    env = {
        "PATH": "/usr/bin:/bin",
        "WORKSPACES": "does-not-exist",
        "RUN_FMT": "true",
    }
    res = subprocess.run(
        ["bash", str(RUN_CHECKS_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res.returncode != 0
    assert "Cargo manifest not found" in res.stderr


def test_install_worker_build_skips_when_present(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    wb = mock_bin / "worker-build"
    wb.write_text("#!/usr/bin/env sh\nexit 0\n")
    wb.chmod(0o755)

    res = subprocess.run(
        ["bash", str(INSTALL_WORKER_BUILD_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": f"{mock_bin}:/usr/bin:/bin"},
    )
    assert res.returncode == 0
    assert "already available" in res.stdout
