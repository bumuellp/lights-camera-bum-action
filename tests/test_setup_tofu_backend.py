"""Unit tests for setup-tofu-backend composite action and init script."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "setup-tofu-backend"
ACTION_FILE = ACTION_DIR / "action.yml"
INIT_SH = ACTION_DIR / "init.sh"


def test_setup_tofu_backend_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Setup OpenTofu Backend"
    for key in ("bucket", "endpoint", "access-key", "secret-key", "key", "region", "cache"):
        assert key in data["inputs"]
    assert data["runs"]["using"] == "composite"

    for step in data["runs"]["steps"]:
        if "run" in step:
            assert "GITHUB_ACTION_PATH" in step["run"]


def test_init_script_masks_credentials_and_configures_plugin_cache(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    tofu_log = tmp_path / "tofu.log"
    github_env = tmp_path / "github_env.txt"
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    mock_tofu = mock_bin / "tofu"
    mock_tofu.write_text(f'#!/usr/bin/env bash\necho "tofu $*" >> "{tofu_log}"\nexit 0\n')
    mock_tofu.chmod(0o755)

    res = subprocess.run(
        ["bash", str(INIT_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "HOME": str(home_dir),
            "GITHUB_ENV": str(github_env),
            "S3_BUCKET": "state-bucket",
            "S3_ENDPOINT": "https://fsn1.your-objectstorage.com",
            "S3_KEY": "mc/terraform.tfstate",
            "S3_REGION": "us-east-1",
            "S3_ACCESS_KEY": "my-access-key",
            "S3_SECRET_KEY": "my-secret-key",
            "STATE_PASSPHRASE": "my-passphrase",
            "CACHE_PROVIDERS": "true",
        },
    )
    assert res.returncode == 0, res.stderr
    assert "::add-mask::my-access-key" in res.stdout
    assert "::add-mask::my-secret-key" in res.stdout
    assert "::add-mask::my-passphrase" in res.stdout

    env_lines = github_env.read_text()
    expected_cache = str(home_dir / ".terraform.d" / "plugin-cache")
    assert f"TF_PLUGIN_CACHE_DIR={expected_cache}" in env_lines
    assert (home_dir / ".terraform.d" / "plugin-cache").is_dir()
    assert "tofu init -backend-config=bucket=state-bucket" in tofu_log.read_text()
