"""Unit tests for pre-commit composite action, tool detection, and execution."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
PRECOMMIT_DIR = ACTION_ROOT / "pre-commit"
ACTION_FILE = PRECOMMIT_DIR / "action.yml"
DETECT_SH = PRECOMMIT_DIR / "detect_tools.sh"
RUN_NATIVE_SH = PRECOMMIT_DIR / "run_pre_commit.sh"
RUN_CONTAINER_SH = PRECOMMIT_DIR / "run_container.sh"


def test_pre_commit_action_manifest_valid_and_delegates_scripts():
    assert ACTION_FILE.is_file()
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["inputs"]["use-container"]["default"] == "false"
    assert data["inputs"]["cache"]["default"] == "true"

    for step in data["runs"]["steps"]:
        if "run" in step:
            assert "GITHUB_ACTION_PATH" in step["run"], (
                "pre-commit steps must delegate to scripts rather than inline bash"
            )


def test_detect_tools_reads_pre_commit_config(tmp_path):
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text(
        """
repos:
  - repo: https://github.com/bumuellp/cabumtain-hook
    rev: v1.6.1
    hooks:
      - id: secret-scan
      - id: shell-lint
      - id: trivy-config
      - id: tofu-fmt
""",
        encoding="utf-8",
    )
    out_file = tmp_path / "github_output.txt"

    res = subprocess.run(
        ["bash", str(DETECT_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_OUTPUT": str(out_file),
            "TRIVY_VERSION": "0.75.0",
        },
    )
    assert res.returncode == 0, res.stderr

    outputs = dict(line.split("=", 1) for line in out_file.read_text().splitlines())
    assert outputs["tools"] == "trufflehog shfmt trivy tofu"
    assert outputs["trivy_enabled"] == "true"
    assert outputs["ansible_enabled"] == "false"
    assert outputs["pytest_enabled"] == "false"
    assert len(outputs["tools_hash"]) == 16


def test_detect_tools_skips_unused_heavy_tools(tmp_path):
    cfg = tmp_path / ".pre-commit-config.yaml"
    cfg.write_text(
        """
repos:
  - repo: https://github.com/bumuellp/cabumtain-hook
    rev: v1.5.0
    hooks:
      - id: commit-msg
      - id: shell-lint
""",
        encoding="utf-8",
    )
    out_file = tmp_path / "github_output.txt"

    res = subprocess.run(
        ["bash", str(DETECT_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "GITHUB_WORKSPACE": str(tmp_path),
            "GITHUB_OUTPUT": str(out_file),
        },
    )
    assert res.returncode == 0, res.stderr
    outputs = dict(line.split("=", 1) for line in out_file.read_text().splitlines())
    assert outputs["tools"] == "shfmt"
    assert outputs["trivy_enabled"] == "false"


def _make_fake_tool(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


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

    # Verify non-zero exit code propagates
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
