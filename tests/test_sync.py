"""Unit tests for sync-rsync-path/sync.sh."""

import os
import subprocess
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
SYNC_SH = ACTION_ROOT / "sync-rsync-path" / "sync.sh"


def test_sync_sh_missing_required_env_vars():
    # Calling without SSH_USER or SSH_HOST must fail immediately
    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env={}
    )
    assert res.returncode != 0
    assert "SSH_USER is required" in res.stderr or "is required" in res.stderr


def test_sync_sh_execution_with_mock_ssh_and_rsync(tmp_path):
    # Create mock ssh and rsync in temp directory
    mock_bin = tmp_path / "mock_bin"
    mock_bin.mkdir()

    mock_ssh = mock_bin / "ssh"
    mock_ssh.write_text(
        '#!/bin/sh\necho "MOCK_SSH: $@" >> ' + str(tmp_path / "ssh.log") + "\nexit 0\n"
    )
    mock_ssh.chmod(0o755)

    mock_rsync = mock_bin / "rsync"
    mock_rsync.write_text(
        '#!/bin/sh\necho "MOCK_RSYNC: $@" >> ' + str(tmp_path / "rsync.log") + "\nexit 0\n"
    )
    mock_rsync.chmod(0o755)

    # Local path to sync
    local_dir = tmp_path / "data"
    local_dir.mkdir()
    (local_dir / "sample.txt").write_text("hello")

    env = {
        "PATH": f"{mock_bin}:{os.environ['PATH']}",
        "SSH_USER": "testuser",
        "SSH_HOST": "remote.example.com",
        "REMOTE_DIRECTORY": "/var/data/sync",
        "LOCAL_PATH": str(local_dir),
        "SSH_KEY_PATH": str(tmp_path / "key"),
        "SSH_PORT": "2222",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0

    ssh_log = (tmp_path / "ssh.log").read_text()
    assert "mkdir -p '/var/data/sync'" in ssh_log
    assert "-p 2222" in ssh_log
    assert "testuser@remote.example.com" in ssh_log

    rsync_log = (tmp_path / "rsync.log").read_text()
    assert "-avz --delete" in rsync_log
    assert "testuser@remote.example.com:/var/data/sync/" in rsync_log
