"""Unit tests for setup-node action and helper scripts."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "setup-node"
ACTION_FILE = ACTION_DIR / "action.yml"
INSTALL_DEPS_SH = ACTION_DIR / "install_deps.sh"
INSTALL_PW_SH = ACTION_DIR / "install_playwright.sh"
RUN_CHECKS_SH = ACTION_DIR / "run_checks.sh"


def test_action_manifest_valid_and_has_no_inline_bash():
    assert ACTION_FILE.is_file()
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Setup Node.js Toolchain"
    for key in (
        "node-version",
        "workspaces",
        "install-deps",
        "install-playwright",
        "run-lint",
        "run-typecheck",
        "run-build",
        "run-test",
    ):
        assert key in data["inputs"]

    for step in data["runs"]["steps"]:
        if "run" in step:
            assert "GITHUB_ACTION_PATH" in step["run"], (
                "setup-node steps must delegate to scripts rather than inline bash"
            )


def test_scripts_are_executable():
    for script in (INSTALL_DEPS_SH, INSTALL_PW_SH, RUN_CHECKS_SH):
        assert script.is_file()
        if not os.access(script, os.X_OK):
            script.chmod(0o755)
        assert os.access(script, os.X_OK)


def test_install_deps_prefers_npm_ci_when_lockfile_present(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    npm_log = tmp_path / "npm.log"
    mock_npm = mock_bin / "npm"
    mock_npm.write_text(f'#!/usr/bin/env bash\necho "npm $*" >> "{npm_log}"\nexit 0\n')
    mock_npm.chmod(0o755)

    ws_ci = tmp_path / "frontend"
    ws_ci.mkdir()
    (ws_ci / "package.json").write_text('{"name":"frontend"}\n')
    (ws_ci / "package-lock.json").write_text("{}\n")

    ws_inst = tmp_path / "tools"
    ws_inst.mkdir()
    (ws_inst / "package.json").write_text('{"name":"tools"}\n')

    res = subprocess.run(
        ["bash", str(INSTALL_DEPS_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": f"{mock_bin}:/usr/bin:/bin", "WORKSPACES": "frontend tools"},
    )
    assert res.returncode == 0, res.stderr
    assert npm_log.read_text().splitlines() == ["npm ci", "npm install"]


def test_run_checks_executes_configured_scripts(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    npm_log = tmp_path / "npm.log"
    mock_npm = mock_bin / "npm"
    mock_npm.write_text(
        f'#!/usr/bin/env bash\necho "$(basename "$PWD"):npm $*" >> "{npm_log}"\nexit 0\n'
    )
    mock_npm.chmod(0o755)

    for pkg in ("app-a", "app-b"):
        d = tmp_path / pkg
        d.mkdir()
        (d / "package.json").write_text('{"name":"pkg"}\n')

    env = {
        "PATH": f"{mock_bin}:/usr/bin:/bin",
        "WORKSPACES": "app-a app-b/",
        "RUN_LINT": "true",
        "LINT_SCRIPT": "lint",
        "RUN_TYPECHECK": "true",
        "TYPECHECK_SCRIPT": "typecheck",
        "RUN_BUILD": "true",
        "BUILD_SCRIPT": "build",
        "RUN_TEST": "true",
        "TEST_SCRIPT": "test:unit",
    }

    res = subprocess.run(
        ["bash", str(RUN_CHECKS_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res.returncode == 0, res.stderr
    assert npm_log.read_text().splitlines() == [
        "app-a:npm run lint",
        "app-b:npm run lint",
        "app-a:npm run typecheck",
        "app-b:npm run typecheck",
        "app-a:npm run build",
        "app-b:npm run build",
        "app-a:npm run test:unit",
        "app-b:npm run test:unit",
    ]


def test_run_checks_fails_on_missing_package_json(tmp_path):
    res = subprocess.run(
        ["bash", str(RUN_CHECKS_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": "/usr/bin:/bin", "WORKSPACES": "missing", "RUN_LINT": "true"},
    )
    assert res.returncode != 0
    assert "package.json not found" in res.stderr
