"""Unit tests for cleanup-docker composite action conditions and failure modes."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_FILE = ACTION_ROOT / "cleanup-docker" / "action.yml"


def test_cleanup_docker_action_exists():
    assert ACTION_FILE.is_file(), "cleanup-docker/action.yml must exist"


def test_cleanup_docker_step_conditions():
    """Verify that cleanup steps use the correct GitHub Actions execution conditions."""
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    steps = data["runs"]["steps"]
    assert len(steps) == 2

    # Step 1: Logs should only display if failure occurred
    log_step = steps[0]
    assert log_step.get("if") == "failure()", "Log display must only trigger on failure()"
    assert "docker compose logs" in log_step["run"]

    # Step 2: Teardown must run always to prevent orphan containers
    down_step = steps[1]
    assert down_step.get("if") == "always()", "Teardown must always execute (if: always())"
    assert "docker compose down -v" in down_step["run"]


def test_cleanup_docker_propagates_daemon_failure(tmp_path):
    """If docker daemon is unavailable, docker compose commands must return non-zero exit code."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()

    # Mock docker to simulate daemon connection error
    mock_docker = mock_bin / "docker"
    mock_docker.write_text("""#!/bin/sh
echo "Cannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?" >&2
exit 1
""")
    mock_docker.chmod(0o755)

    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    down_command = data["runs"]["steps"][1]["run"]
    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
    }

    res = subprocess.run(
        ["bash", "-c", down_command], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 1, "Daemon connection failure must produce non-zero exit code"
    assert "Cannot connect to the Docker daemon" in res.stderr
