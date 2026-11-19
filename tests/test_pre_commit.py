"""Unit tests for generic pre-commit action and mise integration."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
PRECOMMIT_DIR = ACTION_ROOT / "pre-commit"
ACTION_FILE = PRECOMMIT_DIR / "action.yml"
RUN_NATIVE_SH = PRECOMMIT_DIR / "run_pre_commit.sh"
RUN_CONTAINER_SH = PRECOMMIT_DIR / "run_container.sh"
INSTALL_MISE_SH = PRECOMMIT_DIR / "install_mise_tools.sh"


def _make_fake_tool(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def test_pre_commit_action_manifest_is_generic_and_delegates_scripts():
    assert ACTION_FILE.is_file()
    raw = ACTION_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    assert data["inputs"]["use-container"]["default"] == "false"
    assert data["inputs"]["cache"]["default"] == "true"
    assert "cabumtain" not in raw.lower(), "pre-commit action must remain hook-agnostic"

    for key in ("trivy-version", "shfmt-version", "tofu-version", "trufflehog-version"):
        assert key not in data["inputs"], (
            f"tool version '{key}' must not be hardcoded in action.yml"
        )

    for step in data["runs"]["steps"]:
        if "run" in step:
            assert "GITHUB_ACTION_PATH" in step["run"]


def test_install_mise_tools_runs_uv_before_pipx_and_skips_cached(tmp_path):
    home_dir = tmp_path / "home"
    local_bin = home_dir / ".local" / "bin"
    local_bin.mkdir(parents=True)
    mise_log = tmp_path / "mise.log"

    _make_fake_tool(
        local_bin / "mise",
        f'#!/usr/bin/env bash\necho "mise $*" >> "{mise_log}"\nexit 0\n',
    )

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "mise.toml").write_text('[tools]\njq = "1.7.1"\n', encoding="utf-8")

    env = {
        "PATH": f"{local_bin}:/usr/bin:/bin",
        "HOME": str(home_dir),
        "GITHUB_WORKSPACE": str(workspace),
        "REQUIRED_TOOLS": "pipx:yamllint@1.37.1 shfmt@3.14.1 uv@0.13.5",
    }

    res = subprocess.run(
        ["bash", str(INSTALL_MISE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    calls = mise_log.read_text().splitlines()
    assert "mise trust --all --yes" in calls[0]
    assert calls[1] == "mise install --yes"
    assert calls[2] == "mise use --global --yes uv@0.13.5"
    assert calls[3] == "mise use --global --yes pipx:yamllint@1.37.1 shfmt@3.14.1"

    (home_dir / ".config" / "mise").mkdir(parents=True)
    (home_dir / ".config" / "mise" / "config.toml").write_text("", encoding="utf-8")
    mise_log.unlink()
    res2 = subprocess.run(
        ["bash", str(INSTALL_MISE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res2.returncode == 0
    assert "already cached" in res2.stdout


def test_native_runner_propagates_failure_and_handles_spaces_and_args(tmp_path):
    home_dir = tmp_path / "home"
    venv_bin = home_dir / ".local" / "share" / "pre-commit-venv" / "bin"
    venv_bin.mkdir(parents=True)
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()

    git_log = tmp_path / "git.log"
    pc_log = tmp_path / "pc.log"
    _make_fake_tool(
        mock_bin / "git",
        f'#!/usr/bin/env bash\necho "git $*" >> "{git_log}"\nexit 0\n',
    )
    _make_fake_tool(
        venv_bin / "pre-commit",
        f'#!/usr/bin/env bash\npwd >> "{pc_log}"\necho "pc $*" >> "{pc_log}"\nexit 0\n',
    )

    workspace = tmp_path / "path with spaces" / "my project"
    workspace.mkdir(parents=True)

    res = subprocess.run(
        ["bash", str(RUN_NATIVE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:/usr/bin:/bin",
            "HOME": str(home_dir),
            "GITHUB_WORKSPACE": str(workspace),
            "EXTRA_ARGS": "--hook-stage pre-push --all-files --verbose",
        },
    )
    assert res.returncode == 0, res.stderr
    assert "git config --global --add safe.directory *" in git_log.read_text()
    pc_lines = pc_log.read_text().splitlines()
    assert pc_lines[0] == str(workspace)
    assert pc_lines[1] == (
        "pc run --show-diff-on-failure --hook-stage pre-push --all-files --verbose"
    )

    _make_fake_tool(
        venv_bin / "pre-commit",
        '#!/usr/bin/env bash\necho "pre-commit found errors" >&2\nexit 1\n',
    )
    fail_res = subprocess.run(
        ["bash", str(RUN_NATIVE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:/usr/bin:/bin",
            "HOME": str(home_dir),
            "GITHUB_WORKSPACE": str(workspace),
            "EXTRA_ARGS": "--all-files",
        },
    )
    assert fail_res.returncode == 1
    assert "pre-commit found errors" in fail_res.stderr


def test_container_fallback_handles_spaces_and_uid(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    _make_fake_tool(
        mock_bin / "docker",
        f'#!/usr/bin/env bash\necho "DOCKER_ARGS: $*" >> "{docker_log}"\nexit 0\n',
    )

    workspace = tmp_path / "path with spaces" / "my project"
    workspace.mkdir(parents=True)

    res = subprocess.run(
        ["bash", str(RUN_CONTAINER_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "HOME": str(tmp_path),
            "GITHUB_WORKSPACE": str(workspace),
            "EXTRA_ARGS": "--all-files",
        },
    )
    assert res.returncode == 0, res.stderr
    logged = docker_log.read_text()
    assert f"-v {workspace}:/workspace" in logged
    assert f"-u {os.getuid()}:{os.getgid()}" in logged
    assert "pre-commit run --show-diff-on-failure --all-files" in logged
