"""Unit tests for pre-commit composite action failure modes and edge cases."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_FILE = ACTION_ROOT / "pre-commit" / "action.yml"


def test_pre_commit_action_exists():
    assert ACTION_FILE.is_file(), "pre-commit/action.yml must exist"


def get_resolved_script(workspace: Path, extra_args: str = "--all-files") -> str:
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    run_script = data["runs"]["steps"][0]["run"]
    return run_script.replace("${{ github.workspace }}", str(workspace)).replace(
        "${{ inputs.extra-args }}", extra_args
    )


def test_pre_commit_propagates_failure_exit_code(tmp_path):
    """If pre-commit run fails (exit code 1), the docker command must exit with code 1."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    mock_docker = mock_bin / "docker"
    # Mock docker to exit with code 1 when pre-commit fails
    mock_docker.write_text("""#!/bin/sh
echo "pre-commit found errors" >&2
exit 1
""")
    mock_docker.chmod(0o755)

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    script = get_resolved_script(workspace)
    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HOME": str(tmp_path),
    }

    res = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 1, "Failure exit code must be propagated, not swallowed"
    assert "pre-commit found errors" in res.stderr


def test_pre_commit_handles_workspace_with_spaces(tmp_path):
    """Workspace path containing spaces must be properly quoted in docker mount."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    log_file = tmp_path / "docker.log"

    mock_docker = mock_bin / "docker"
    mock_docker.write_text(f"""#!/bin/sh
echo "DOCKER_ARGS: $@" >> "{log_file}"
exit 0
""")
    mock_docker.chmod(0o755)

    workspace_with_spaces = tmp_path / "path with spaces" / "my project"
    workspace_with_spaces.mkdir(parents=True)

    script = get_resolved_script(workspace_with_spaces)
    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HOME": str(tmp_path),
    }

    res = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}"

    logged = log_file.read_text()
    assert f"-v {workspace_with_spaces}:/workspace" in logged


def test_pre_commit_handles_complex_extra_args(tmp_path):
    """Complex extra-args with multiple flags and values must be passed correctly to container."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    log_file = tmp_path / "docker.log"

    mock_docker = mock_bin / "docker"
    mock_docker.write_text(f"""#!/bin/sh
echo "DOCKER_ARGS: $@" >> "{log_file}"
exit 0
""")
    mock_docker.chmod(0o755)

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    complex_args = "--hook-stage pre-push --all-files --verbose"
    script = get_resolved_script(workspace, extra_args=complex_args)
    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HOME": str(tmp_path),
    }

    res = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0

    logged = log_file.read_text()
    assert f"pre-commit run {complex_args}" in logged


def test_pre_commit_enforces_safe_directory_and_non_root_uid():
    """Action must set git safe.directory and run with current user's UID to prevent ownership errors."""
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    run_script = data["runs"]["steps"][0]["run"]
    assert 'git config --global --add safe.directory "*"' in run_script
    assert '-u "$(id -u):$(id -g)"' in run_script
    assert "ghcr.io/bumuellp/lint-tools:latest" in run_script
