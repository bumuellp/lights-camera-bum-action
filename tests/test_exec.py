"""Unit tests for run-authorized-ssh-script/exec.sh."""

import os
import subprocess
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
EXEC_SH = ACTION_ROOT / "run-authorized-ssh-script" / "exec.sh"


def test_exec_sh_missing_required_env_vars():
    res = subprocess.run(
        ["bash", str(EXEC_SH)], capture_output=True, text=True, check=False, env={}
    )
    assert res.returncode != 0
    assert "SSH_USER is required" in res.stderr or "is required" in res.stderr


def test_exec_sh_execution_with_mock_ssh(tmp_path):
    mock_bin = tmp_path / "mock_bin"
    mock_bin.mkdir()

    mock_ssh = mock_bin / "ssh"
    # Read stdin payload and record args
    mock_ssh.write_text(
        """#!/bin/sh
cat - > """
        + str(tmp_path / "stdin.log")
        + """
echo "MOCK_SSH: $@" >> """
        + str(tmp_path / "ssh.log")
        + """
exit 0
"""
    )
    mock_ssh.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ['PATH']}",
        "SSH_USER": "deployer",
        "SSH_HOST": "node1.homelab",
        "REMOTE_COMMAND": "/usr/local/bin/deploy.sh",
        "ENV_PAYLOAD": "SECRET_KEY=12345\nNODE_ENV=prod",
        "SSH_KEY_PATH": str(tmp_path / "deploy_key"),
        "SSH_PORT": "2200",
    }

    res = subprocess.run(
        ["bash", str(EXEC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0

    ssh_log = (tmp_path / "ssh.log").read_text()
    assert "-p 2200" in ssh_log
    assert "deployer@node1.homelab" in ssh_log
    assert "/usr/local/bin/deploy.sh" in ssh_log

    stdin_log = (tmp_path / "stdin.log").read_text()
    assert stdin_log == "SECRET_KEY=12345\nNODE_ENV=prod"
