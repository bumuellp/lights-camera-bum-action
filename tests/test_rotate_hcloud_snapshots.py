"""Unit tests for rotate-hcloud-snapshots action and rotate.sh script."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "rotate-hcloud-snapshots"
ACTION_FILE = ACTION_DIR / "action.yml"
ROTATE_SH = ACTION_DIR / "rotate.sh"


def test_action_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Rotate Hetzner Cloud Snapshots"
    assert "inputs" in data
    assert "token" in data["inputs"]
    assert data["inputs"]["token"]["required"] is True
    assert "label-selector" in data["inputs"]
    assert data["inputs"]["label-selector"]["required"] is True
    assert "keep" in data["inputs"]
    assert data["inputs"]["keep"].get("default") == "1"


def test_rotate_sh_executable():
    assert ROTATE_SH.is_file(), "rotate.sh must exist"
    if not os.access(ROTATE_SH, os.X_OK):
        ROTATE_SH.chmod(0o755)
    assert os.access(ROTATE_SH, os.X_OK), "rotate.sh must be executable"


def test_rotate_sh_missing_token():
    res = subprocess.run(
        ["bash", str(ROTATE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert res.returncode != 0
    assert "token" in res.stderr.lower()


def test_rotate_sh_missing_label_selector():
    res = subprocess.run(
        ["bash", str(ROTATE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={"HCLOUD_TOKEN": "mock-token", "PATH": os.environ.get("PATH", "")},
    )
    assert res.returncode != 0
    assert "label-selector" in res.stderr.lower()


def test_rotate_sh_invalid_keep_count():
    res = subprocess.run(
        ["bash", str(ROTATE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "HCLOUD_TOKEN": "mock-token",
            "LABEL_SELECTOR": "role=test",
            "KEEP_COUNT": "invalid",
            "PATH": os.environ.get("PATH", ""),
        },
    )
    assert res.returncode != 0
    assert "integer" in res.stderr.lower()


def test_rotate_sh_missing_binary():
    env = {
        "PATH": "/usr/bin:/bin",
        "HCLOUD_TOKEN": "mock-token",
        "LABEL_SELECTOR": "role=test",
    }
    res = subprocess.run(
        ["bash", str(ROTATE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode != 0
    assert "'hcloud' CLI is required" in res.stderr


def test_rotate_sh_retention_mock(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    call_log = tmp_path / "calls.log"

    mock_hcloud = mock_bin / "hcloud"
    mock_hcloud.write_text(f"""#!/usr/bin/env python3
import sys

args = sys.argv[1:]
with open('{call_log}', 'a') as f:
    f.write(' '.join(args) + '\\n')

if 'image' in args and 'list' in args:
    # Print 3 snapshots in tab-separated format: id \t created \t description
    print("101\\t2026-10-24T05:00:00Z\\timage-newest")
    print("102\\t2026-10-24T04:00:00Z\\timage-older")
    print("103\\t2026-10-24T03:00:00Z\\timage-oldest")
    sys.exit(0)

if 'image' in args and 'delete' in args:
    sys.exit(0)

sys.exit(0)
""")
    mock_hcloud.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "mock-token-xyz",
        "LABEL_SELECTOR": "role=golden-image",
        "KEEP_COUNT": "1",
    }

    res = subprocess.run(
        ["bash", str(ROTATE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}\nOutput: {res.stdout}"
    assert "Found 3 snapshot(s)" in res.stdout
    assert "Deleting old snapshot: ID=102" in res.stdout
    assert "Deleting old snapshot: ID=103" in res.stdout
    assert "ID=101" not in res.stdout

    calls = call_log.read_text().splitlines()
    assert any("image list" in c for c in calls)
    delete_calls = [c for c in calls if "image delete" in c]
    assert len(delete_calls) == 2
    assert any("102" in c for c in delete_calls)
    assert any("103" in c for c in delete_calls)
    assert not any("101" in c for c in delete_calls)


def test_rotate_sh_no_deletion_when_under_limit(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    call_log = tmp_path / "calls.log"

    mock_hcloud = mock_bin / "hcloud"
    mock_hcloud.write_text(f"""#!/usr/bin/env python3
import sys

args = sys.argv[1:]
with open('{call_log}', 'a') as f:
    f.write(' '.join(args) + '\\n')

if 'image' in args and 'list' in args:
    print("201\\t2026-10-24T05:00:00Z\\timage-sole")
    sys.exit(0)

sys.exit(0)
""")
    mock_hcloud.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "mock-token-xyz",
        "LABEL_SELECTOR": "role=golden-image",
        "KEEP_COUNT": "1",
    }

    res = subprocess.run(
        ["bash", str(ROTATE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}\nOutput: {res.stdout}"
    assert "Found 1 snapshot(s)" in res.stdout
    assert "No old snapshots to delete" in res.stdout

    calls = call_log.read_text().splitlines()
    delete_calls = [c for c in calls if "image delete" in c]
    assert len(delete_calls) == 0
