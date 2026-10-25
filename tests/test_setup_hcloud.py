"""Unit tests for setup-hcloud action and setup.sh script."""

import os
import subprocess
import tarfile
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "setup-hcloud"
ACTION_FILE = ACTION_DIR / "action.yml"
SETUP_SH = ACTION_DIR / "setup.sh"


def test_action_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Setup Hetzner Cloud CLI"
    assert "inputs" in data
    assert "version" in data["inputs"]
    assert "token" in data["inputs"]
    assert "cache" in data["inputs"]


def test_setup_sh_executable():
    assert SETUP_SH.is_file(), "setup.sh must exist"
    if not os.access(SETUP_SH, os.X_OK):
        SETUP_SH.chmod(0o755)
    assert os.access(SETUP_SH, os.X_OK), "setup.sh must be executable"


def test_setup_sh_downloads_and_installs(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    github_path_file = tmp_path / "github_path"
    github_env_file = tmp_path / "github_env"

    # Create dummy archive containing a mock hcloud binary
    tar_path = tmp_path / "hcloud.tar.gz"
    dummy_hcloud = tmp_path / "hcloud"
    dummy_hcloud.write_text("#!/usr/bin/env bash\necho 'hcloud v1.70.2'\n")
    dummy_hcloud.chmod(0o755)

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(dummy_hcloud, arcname="hcloud")

    # Mock curl to copy tar_path when requested
    mock_curl = mock_bin / "curl"
    mock_curl.write_text(f"""#!/usr/bin/env bash
cat '{tar_path}'
""")
    mock_curl.chmod(0o755)

    env = {
        "HOME": str(home_dir),
        "PATH": f"{mock_bin}:/usr/bin:/bin",
        "GITHUB_PATH": str(github_path_file),
        "GITHUB_ENV": str(github_env_file),
        "HCLOUD_TOKEN": "mock-hcloud-secret",
        "HCLOUD_VERSION": "v1.70.2",
    }

    res = subprocess.run(
        ["bash", str(SETUP_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "installed successfully" in res.stdout
    assert (home_dir / ".local" / "bin" / "hcloud").is_file()

    # Check GITHUB_PATH and GITHUB_ENV
    assert str(home_dir / ".local" / "bin") in github_path_file.read_text()
    assert "HCLOUD_TOKEN=mock-hcloud-secret" in github_env_file.read_text()


def test_setup_sh_already_present(tmp_path):
    home_dir = tmp_path / "home"
    bin_dir = home_dir / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    existing_hcloud = bin_dir / "hcloud"
    existing_hcloud.write_text("#!/usr/bin/env bash\necho 'already here'\n")
    existing_hcloud.chmod(0o755)

    env = {
        "HOME": str(home_dir),
        "PATH": "/usr/bin:/bin",
    }

    res = subprocess.run(
        ["bash", str(SETUP_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "already installed" in res.stdout
