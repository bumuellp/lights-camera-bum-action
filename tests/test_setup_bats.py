"""Unit tests for setup-bats action and setup.sh script."""

import os
import subprocess
import tarfile
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "setup-bats"
ACTION_FILE = ACTION_DIR / "action.yml"
SETUP_SH = ACTION_DIR / "setup.sh"


def test_action_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Setup Bats Testing Framework"
    assert "inputs" in data
    assert "version" in data["inputs"]
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

    # Create dummy bats-core archive with an install.sh script
    archive_src = tmp_path / "bats-core-1.13.0"
    archive_src.mkdir()
    install_sh = archive_src / "install.sh"
    install_sh.write_text("""#!/usr/bin/env bash
PREFIX="$1"
mkdir -p "${PREFIX}/bin"
printf '#!/usr/bin/env bash\\necho "Bats 1.13.0"\\n' > "${PREFIX}/bin/bats"
chmod +x "${PREFIX}/bin/bats"
""")
    install_sh.chmod(0o755)

    tar_path = tmp_path / "bats-core.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(archive_src, arcname="bats-core-1.13.0")

    mock_curl = mock_bin / "curl"
    mock_curl.write_text(f"""#!/usr/bin/env bash
cat '{tar_path}'
""")
    mock_curl.chmod(0o755)

    env = {
        "HOME": str(home_dir),
        "PATH": f"{mock_bin}:/usr/bin:/bin",
        "GITHUB_PATH": str(github_path_file),
        "BATS_VERSION": "v1.13.0",
    }

    res = subprocess.run(
        ["bash", str(SETUP_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "installed successfully" in res.stdout
    assert (home_dir / ".local" / "bin" / "bats").is_file()
    assert str(home_dir / ".local" / "bin") in github_path_file.read_text()


def test_setup_sh_already_present(tmp_path):
    home_dir = tmp_path / "home"
    bin_dir = home_dir / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    existing_bats = bin_dir / "bats"
    existing_bats.write_text("#!/usr/bin/env bash\necho 'Bats 1.13.0'\n")
    existing_bats.chmod(0o755)

    env = {
        "HOME": str(home_dir),
        "PATH": "/usr/bin:/bin",
    }

    res = subprocess.run(
        ["bash", str(SETUP_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "already installed" in res.stdout
