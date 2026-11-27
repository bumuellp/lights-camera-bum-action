"""Unit tests for tofu-module-test composite action, reusable workflow, and script."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "tofu-module-test"
ACTION_FILE = ACTION_DIR / "action.yml"
SCRIPT_FILE = ACTION_DIR / "validate_and_test.sh"
WORKFLOW_FILE = ACTION_ROOT / ".github" / "workflows" / "tofu-test.yml"


def _make_mock_tofu(tmp_path: Path, exit_code_on_test: int = 0) -> tuple[Path, Path]:
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir(exist_ok=True)
    log_file = tmp_path / "tofu.log"
    mock_tofu = mock_bin / "tofu"
    mock_tofu.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "tofu $*" >> "{log_file}"\n'
        'for arg in "$@"; do\n'
        '  if [ "$arg" = "test" ]; then\n'
        f"    exit {exit_code_on_test}\n"
        "  fi\n"
        "done\n"
        "exit 0\n"
    )
    mock_tofu.chmod(0o755)
    return mock_bin, log_file


def test_tofu_module_test_action_and_workflow_valid():
    assert ACTION_FILE.is_file()
    assert WORKFLOW_FILE.is_file()

    action_data = yaml.safe_load(ACTION_FILE.read_text(encoding="utf-8"))
    assert action_data["runs"]["using"] == "composite"
    for key in ("modules-glob", "tofu-version", "tofu-version-file", "cache", "run-tests"):
        assert key in action_data["inputs"]

    wf_data = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    assert wf_data["permissions"] == {"contents": "read"}
    assert "concurrency" in wf_data
    assert "workflow_call" in wf_data["on"]


def test_validate_and_test_runs_validate_on_all_and_test_where_present(tmp_path):
    mod_a = tmp_path / "modules" / "alpha"
    mod_b = tmp_path / "modules" / "beta"
    (mod_b / "tests").mkdir(parents=True)
    mod_a.mkdir(parents=True)
    (mod_b / "tests" / "basic.tftest.hcl").write_text("# mock test\n")

    mock_bin, log_file = _make_mock_tofu(tmp_path)
    cache_dir = tmp_path / "plugin-cache"

    res = subprocess.run(
        ["bash", str(SCRIPT_FILE)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "MODULES_GLOB": "modules/*",
            "RUN_TESTS": "true",
            "CACHE_PROVIDERS": "true",
            "TF_PLUGIN_CACHE_DIR": str(cache_dir),
        },
    )
    assert res.returncode == 0, res.stderr
    assert cache_dir.is_dir()

    log_lines = log_file.read_text().splitlines()
    assert "tofu -chdir=modules/alpha init -backend=false -input=false" in log_lines
    assert "tofu -chdir=modules/alpha validate" in log_lines
    assert "tofu -chdir=modules/alpha test" not in log_lines
    assert "tofu -chdir=modules/beta init -backend=false -input=false" in log_lines
    assert "tofu -chdir=modules/beta validate" in log_lines
    assert "tofu -chdir=modules/beta test" in log_lines


def test_validate_and_test_skips_tests_and_unsets_cache_when_disabled(tmp_path):
    mod_b = tmp_path / "modules" / "beta"
    (mod_b / "tests").mkdir(parents=True)
    (mod_b / "tests" / "basic.tftest.hcl").write_text("# mock test\n")

    env_log = tmp_path / "env.log"
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir(exist_ok=True)
    log_file = tmp_path / "tofu.log"
    mock_tofu = mock_bin / "tofu"
    mock_tofu.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "TF_PLUGIN_CACHE_DIR=${{TF_PLUGIN_CACHE_DIR:-UNSET}}" >> "{env_log}"\n'
        f'echo "tofu $*" >> "{log_file}"\n'
        "exit 0\n"
    )
    mock_tofu.chmod(0o755)

    missing_cache = tmp_path / "does-not-exist"
    res = subprocess.run(
        ["bash", str(SCRIPT_FILE)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "MODULES_GLOB": "modules/*",
            "RUN_TESTS": "false",
            "CACHE_PROVIDERS": "false",
            "TF_PLUGIN_CACHE_DIR": str(missing_cache),
        },
    )
    assert res.returncode == 0, res.stderr
    assert "test" not in log_file.read_text()
    assert not missing_cache.exists()
    assert "TF_PLUGIN_CACHE_DIR=UNSET" in env_log.read_text()


def test_validate_and_test_supports_multiple_globs_and_skips_files(tmp_path):
    mod_a = tmp_path / "modules" / "alpha"
    stack_b = tmp_path / "stacks" / "prod"
    mod_a.mkdir(parents=True)
    stack_b.mkdir(parents=True)
    (tmp_path / "modules" / "README.md").write_text("not a dir\n")

    mock_bin, log_file = _make_mock_tofu(tmp_path)
    res = subprocess.run(
        ["bash", str(SCRIPT_FILE)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "MODULES_GLOB": "modules/* stacks/*",
            "CACHE_PROVIDERS": "false",
        },
    )
    assert res.returncode == 0, res.stderr
    log_text = log_file.read_text()
    assert "tofu -chdir=modules/alpha validate" in log_text
    assert "tofu -chdir=stacks/prod validate" in log_text
    assert "README.md" not in log_text


def test_validate_and_test_fails_when_no_modules_match(tmp_path):
    mock_bin, _ = _make_mock_tofu(tmp_path)
    res = subprocess.run(
        ["bash", str(SCRIPT_FILE)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "MODULES_GLOB": "modules/*",
        },
    )
    assert res.returncode != 0
    assert "No OpenTofu modules found" in res.stderr


def test_validate_and_test_propagates_tofu_test_failure(tmp_path):
    mod_b = tmp_path / "modules" / "beta"
    mod_b.mkdir(parents=True)
    (mod_b / "root.tftest.json").write_text("{}\n")

    mock_bin, _ = _make_mock_tofu(tmp_path, exit_code_on_test=2)
    res = subprocess.run(
        ["bash", str(SCRIPT_FILE)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "MODULES_GLOB": "modules/*",
        },
    )
    assert res.returncode == 2
