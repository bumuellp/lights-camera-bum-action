"""Unit tests for decrypt-sops action and decrypt.sh script."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "decrypt-sops"
ACTION_FILE = ACTION_DIR / "action.yml"
DECRYPT_SH = ACTION_DIR / "decrypt.sh"


def test_action_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Decrypt SOPS Secrets"
    assert "inputs" in data
    assert "age-key" in data["inputs"]
    assert "file" in data["inputs"]
    assert "output" in data["inputs"]
    assert "mode" in data["inputs"]
    assert "outputs" in data
    assert "decrypted" in data["outputs"]


def test_decrypt_sh_executable():
    assert DECRYPT_SH.is_file(), "decrypt.sh must exist"
    if not os.access(DECRYPT_SH, os.X_OK):
        DECRYPT_SH.chmod(0o755)
    assert os.access(DECRYPT_SH, os.X_OK), "decrypt.sh must be executable"


def test_decrypt_sh_missing_age_key(tmp_path):
    # When AGE_KEY is empty, it should gracefully skip and write decrypted=false
    gh_output = tmp_path / "github_output"
    gh_output.touch()

    env = {
        "PATH": os.environ.get("PATH", ""),
        "AGE_KEY": "",
        "FILE_PATH": str(tmp_path / "secret.enc.yaml"),
        "OUTPUT_PATH": str(tmp_path / "secret.yaml"),
        "GITHUB_OUTPUT": str(gh_output),
    }

    result = subprocess.run([str(DECRYPT_SH)], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "No SOPS_AGE_KEY provided" in result.stdout
    assert "decrypted=false" in gh_output.read_text()


def test_decrypt_sh_missing_target_file(tmp_path):
    # When file does not exist, it should gracefully skip and write decrypted=false
    gh_output = tmp_path / "github_output"
    gh_output.touch()

    env = {
        "PATH": os.environ.get("PATH", ""),
        "AGE_KEY": "AGE-SECRET-KEY-1TEST",
        "FILE_PATH": str(tmp_path / "nonexistent.enc.yaml"),
        "OUTPUT_PATH": str(tmp_path / "secret.yaml"),
        "GITHUB_OUTPUT": str(gh_output),
    }

    result = subprocess.run([str(DECRYPT_SH)], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "does not exist" in result.stdout
    assert "decrypted=false" in gh_output.read_text()
