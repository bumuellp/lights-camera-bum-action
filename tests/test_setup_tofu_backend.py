"""Unit tests for setup-tofu-backend composite action."""

from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "setup-tofu-backend"
ACTION_FILE = ACTION_DIR / "action.yml"


def test_setup_tofu_backend_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Setup OpenTofu Backend"
    assert "inputs" in data
    assert "bucket" in data["inputs"]
    assert "endpoint" in data["inputs"]
    assert "access-key" in data["inputs"]
    assert "secret-key" in data["inputs"]
    assert "key" in data["inputs"]
    assert "region" in data["inputs"]
    assert "runs" in data
    assert data["runs"]["using"] == "composite"
