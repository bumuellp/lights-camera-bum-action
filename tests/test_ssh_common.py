"""Unit tests for common/ssh-common.sh."""

import subprocess
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
SSH_COMMON_SH = ACTION_ROOT / "common" / "ssh-common.sh"


def test_ssh_common_missing_user():
    cmd = f'source "{SSH_COMMON_SH}" && setup_ssh_env'
    res = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        check=False,
        env={"SSH_HOST": "example.com"},
    )
    assert res.returncode != 0
    assert "SSH_USER is required" in res.stderr


def test_ssh_common_missing_host():
    cmd = f'source "{SSH_COMMON_SH}" && setup_ssh_env'
    res = subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
        check=False,
        env={"SSH_USER": "testuser"},
    )
    assert res.returncode != 0
    assert "SSH_HOST is required" in res.stderr


def test_ssh_common_defaults():
    cmd = f"""
    source "{SSH_COMMON_SH}"
    setup_ssh_env
    echo "REMOTE:$remote"
    echo "ARGS:${{ssh_args[*]}}"
    echo "TRANSPORT:$ssh_transport"
    """
    env = {
        "SSH_USER": "testuser",
        "SSH_HOST": "remote.local",
    }
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=False, env=env)
    assert res.returncode == 0
    assert "REMOTE:testuser@remote.local" in res.stdout
    assert "-i /runner_ssh_key -o StrictHostKeyChecking=accept-new" in res.stdout
    assert "-p" not in res.stdout


def test_ssh_common_custom_key_and_port():
    cmd = f"""
    source "{SSH_COMMON_SH}"
    setup_ssh_env
    echo "REMOTE:$remote"
    echo "ARGS:${{ssh_args[*]}}"
    echo "TRANSPORT:$ssh_transport"
    """
    env = {
        "SSH_USER": "admin",
        "SSH_HOST": "server.internal",
        "SSH_KEY_PATH": "/custom/id_ed25519",
        "SSH_PORT": "2222",
    }
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=False, env=env)
    assert res.returncode == 0
    assert "REMOTE:admin@server.internal" in res.stdout
    assert "-i /custom/id_ed25519 -o StrictHostKeyChecking=accept-new -p 2222" in res.stdout
    assert "ssh -i '/custom/id_ed25519' -o StrictHostKeyChecking=accept-new -p 2222" in res.stdout


def test_ssh_common_key_with_spaces():
    cmd = f"""
    source "{SSH_COMMON_SH}"
    setup_ssh_env
    echo "TRANSPORT:$ssh_transport"
    """
    env = {
        "SSH_USER": "admin",
        "SSH_HOST": "server.internal",
        "SSH_KEY_PATH": "/custom path/id ed25519",
    }
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=False, env=env)
    assert res.returncode == 0
    assert "ssh -i '/custom path/id ed25519' -o StrictHostKeyChecking=accept-new" in res.stdout
