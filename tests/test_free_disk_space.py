"""Unit tests for free-disk-space composite action failure modes and edge cases."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_FILE = ACTION_ROOT / "free-disk-space" / "action.yml"


def test_free_disk_space_action_exists():
    assert ACTION_FILE.is_file(), "free-disk-space/action.yml must exist"


def test_free_disk_space_idempotent_when_paths_do_not_exist(tmp_path):
    """rm -rf must succeed idempotently even if target paths are already absent."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    log_file = tmp_path / "cleanup.log"

    # Mock sudo to execute command directly
    mock_sudo = mock_bin / "sudo"
    mock_sudo.write_text(f"""#!/bin/sh
echo "SUDO: $@" >> "{log_file}"
"$@"
""")
    mock_sudo.chmod(0o755)

    # Mock df
    mock_df = mock_bin / "df"
    mock_df.write_text("""#!/bin/sh
echo "Filesystem Size Used Avail Use% Mounted on"
exit 0
""")
    mock_df.chmod(0o755)

    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Point rm targets to non-existent temp paths to test rm -rf behavior
    rm_step = data["runs"]["steps"][1]["run"]
    non_existent_target = str(tmp_path / "non_existent_toolchain")
    test_script = rm_step.replace("/usr/share/dotnet", non_existent_target)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
    }

    res = subprocess.run(
        ["bash", "-c", test_script], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0, (
        f"rm -rf on absent directories must succeed idempotently: {res.stderr}"
    )


def test_free_disk_space_propagates_deletion_failure(tmp_path):
    """If rm encounters a fatal error (e.g. read-only filesystem), failure must propagate."""
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()

    mock_sudo = mock_bin / "sudo"
    mock_sudo.write_text("""#!/bin/sh
"$@"
""")
    mock_sudo.chmod(0o755)

    # Mock rm to simulate filesystem failure
    mock_rm = mock_bin / "rm"
    mock_rm.write_text("""#!/bin/sh
echo "rm: cannot remove: Read-only file system" >&2
exit 1
""")
    mock_rm.chmod(0o755)

    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    rm_step = data["runs"]["steps"][1]["run"]
    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
    }

    res = subprocess.run(
        ["bash", "-c", rm_step], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode != 0, "Fatal deletion error must not be silently masked"
    assert "Read-only file system" in res.stderr
