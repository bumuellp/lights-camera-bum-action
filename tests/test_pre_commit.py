"""Unit tests for generic pre-commit action, tool discovery, and mise integration."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
PRECOMMIT_DIR = ACTION_ROOT / "pre-commit"
ACTION_FILE = PRECOMMIT_DIR / "action.yml"
RUN_NATIVE_SH = PRECOMMIT_DIR / "run_pre_commit.sh"
RUN_CONTAINER_SH = PRECOMMIT_DIR / "run_container.sh"
INSTALL_MISE_SH = PRECOMMIT_DIR / "install_mise_tools.sh"

sys.path.insert(0, str(PRECOMMIT_DIR))
from discover_tools import discover_tools  # noqa: E402


def _make_fake_tool(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def test_pre_commit_action_manifest_is_generic_and_delegates_scripts():
    assert ACTION_FILE.is_file()
    raw = ACTION_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    assert data["inputs"]["use-container"]["default"] == "false"
    assert data["inputs"]["cache"]["default"] == "true"
    assert "cabumtain" not in raw.lower(), "pre-commit action must remain hook-agnostic"

    for key in ("trivy-version", "shfmt-version", "tofu-version", "trufflehog-version"):
        assert key not in data["inputs"], (
            f"tool version '{key}' must not be hardcoded in action.yml"
        )

    for step in data["runs"]["steps"]:
        if "run" in step:
            assert "GITHUB_ACTION_PATH" in step["run"]


def test_discover_tools_reads_companion_manifest_description_tags_and_mise_toml(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    pc_home = tmp_path / "pc-home"
    pc_home.mkdir()

    # Remote hook repo 1: companion .pre-commit-tools.yaml
    repo1_dir = pc_home / "repo_a"
    repo1_dir.mkdir()
    (repo1_dir / ".pre-commit-tools.yaml").write_text(
        """
hook-one:
  - "tool-alpha@1.2.3"
hook-unused:
  - "should-not-install@9.9.9"
hook-security:
  - "trivy@0.75.0"
""",
        encoding="utf-8",
    )

    # Remote hook repo 2: [tools: ...] in .pre-commit-hooks.yaml description
    repo2_dir = pc_home / "repo_b"
    repo2_dir.mkdir()
    (repo2_dir / ".pre-commit-hooks.yaml").write_text(
        """
- id: docker-check
  name: Docker Check
  description: "Lint Dockerfiles [tools: hadolint@2.12.0]"
  entry: hadolint
  language: system
- id: skipped-hook
  name: Skipped
  description: "[tools: unused-b@1.0.0]"
  entry: "true"
  language: system
""",
        encoding="utf-8",
    )

    with sqlite3.connect(pc_home / "db.db") as conn:
        conn.execute("CREATE TABLE repos (repo TEXT, ref TEXT, path TEXT)")
        conn.execute(
            "INSERT INTO repos VALUES (?, ?, ?)",
            ("https://example.com/hooks-a", "v1.0.0", str(repo1_dir)),
        )
        conn.execute(
            "INSERT INTO repos VALUES (?, ?, ?)",
            ("https://example.com/hooks-b", "v2.0.0", str(repo2_dir)),
        )

    (workspace / ".pre-commit-config.yaml").write_text(
        """
repos:
  - repo: https://example.com/hooks-a
    rev: v1.0.0
    hooks:
      - id: hook-one
      - id: hook-security
  - repo: https://example.com/hooks-b
    rev: v2.0.0
    hooks:
      - id: docker-check
  - repo: local
    hooks:
      - id: local-lint
        name: Local
        description: "Local check [requires: shfmt@3.14.1]"
        entry: shfmt
        language: system
""",
        encoding="utf-8",
    )
    (workspace / "mise.toml").write_text('[tools]\njq = "1.7.1"\n', encoding="utf-8")

    result = discover_tools(workspace, pc_home, extra_tools_raw="bats@1.13.0")
    assert result["tools"] == (
        "bats@1.13.0 hadolint@2.12.0 shfmt@3.14.1 tool-alpha@1.2.3 trivy@0.75.0"
    )
    assert result["needs_mise"] == "true"
    assert result["has_trivy"] == "true"
    assert len(result["tools_hash"]) == 16


def test_discover_tools_handles_empty_config(tmp_path):
    result = discover_tools(tmp_path, tmp_path / "missing-pc")
    assert result["tools"] == ""
    assert result["needs_mise"] == "false"
    assert result["has_trivy"] == "false"


def test_install_mise_tools_runs_uv_before_pipx_and_skips_cached(tmp_path):
    home_dir = tmp_path / "home"
    local_bin = home_dir / ".local" / "bin"
    local_bin.mkdir(parents=True)
    mise_log = tmp_path / "mise.log"

    _make_fake_tool(
        local_bin / "mise",
        f'#!/usr/bin/env bash\necho "mise $*" >> "{mise_log}"\nexit 0\n',
    )

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "mise.toml").write_text('[tools]\njq = "1.7.1"\n', encoding="utf-8")

    env = {
        "PATH": f"{local_bin}:/usr/bin:/bin",
        "HOME": str(home_dir),
        "GITHUB_WORKSPACE": str(workspace),
        "REQUIRED_TOOLS": "pipx:yamllint@1.37.1 shfmt@3.14.1 uv@0.13.5",
    }

    res = subprocess.run(
        ["bash", str(INSTALL_MISE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    calls = mise_log.read_text().splitlines()
    assert "mise trust --all --yes" in calls[0]
    assert calls[1] == "mise install --yes"
    assert calls[2] == "mise use --global --yes uv@0.13.5"
    assert calls[3] == "mise use --global --yes pipx:yamllint@1.37.1 shfmt@3.14.1"

    # Re-running with matching marker & config skips mise use
    (home_dir / ".config" / "mise").mkdir(parents=True)
    (home_dir / ".config" / "mise" / "config.toml").write_text("", encoding="utf-8")
    mise_log.unlink()
    res2 = subprocess.run(
        ["bash", str(INSTALL_MISE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res2.returncode == 0
    assert "already cached" in res2.stdout


def test_native_runner_propagates_failure_and_handles_spaces_and_args(tmp_path):
    home_dir = tmp_path / "home"
    venv_bin = home_dir / ".local" / "share" / "pre-commit-venv" / "bin"
    venv_bin.mkdir(parents=True)
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()

    git_log = tmp_path / "git.log"
    pc_log = tmp_path / "pc.log"
    _make_fake_tool(
        mock_bin / "git",
        f'#!/usr/bin/env bash\necho "git $*" >> "{git_log}"\nexit 0\n',
    )
    _make_fake_tool(
        venv_bin / "pre-commit",
        f'#!/usr/bin/env bash\npwd >> "{pc_log}"\necho "pc $*" >> "{pc_log}"\nexit 0\n',
    )

    workspace = tmp_path / "path with spaces" / "my project"
    workspace.mkdir(parents=True)

    res = subprocess.run(
        ["bash", str(RUN_NATIVE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:/usr/bin:/bin",
            "HOME": str(home_dir),
            "GITHUB_WORKSPACE": str(workspace),
            "EXTRA_ARGS": "--hook-stage pre-push --all-files --verbose",
        },
    )
    assert res.returncode == 0, res.stderr
    assert "git config --global --add safe.directory *" in git_log.read_text()
    pc_lines = pc_log.read_text().splitlines()
    assert pc_lines[0] == str(workspace)
    assert pc_lines[1] == (
        "pc run --show-diff-on-failure --hook-stage pre-push --all-files --verbose"
    )

    _make_fake_tool(
        venv_bin / "pre-commit",
        '#!/usr/bin/env bash\necho "pre-commit found errors" >&2\nexit 1\n',
    )
    fail_res = subprocess.run(
        ["bash", str(RUN_NATIVE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:/usr/bin:/bin",
            "HOME": str(home_dir),
            "GITHUB_WORKSPACE": str(workspace),
            "EXTRA_ARGS": "--all-files",
        },
    )
    assert fail_res.returncode == 1
    assert "pre-commit found errors" in fail_res.stderr


def test_container_fallback_handles_spaces_and_uid(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    docker_log = tmp_path / "docker.log"
    _make_fake_tool(
        mock_bin / "docker",
        f'#!/usr/bin/env bash\necho "DOCKER_ARGS: $*" >> "{docker_log}"\nexit 0\n',
    )

    workspace = tmp_path / "path with spaces" / "my project"
    workspace.mkdir(parents=True)

    res = subprocess.run(
        ["bash", str(RUN_CONTAINER_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "HOME": str(tmp_path),
            "GITHUB_WORKSPACE": str(workspace),
            "EXTRA_ARGS": "--all-files",
        },
    )
    assert res.returncode == 0, res.stderr
    logged = docker_log.read_text()
    assert f"-v {workspace}:/workspace" in logged
    assert f"-u {os.getuid()}:{os.getgid()}" in logged
    assert "pre-commit run --show-diff-on-failure --all-files" in logged
