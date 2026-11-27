"""Unit tests for ansible-test composite action, reusable workflow, and scripts."""

import os
import subprocess
import sys
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "ansible-test"
ACTION_FILE = ACTION_DIR / "action.yml"
SETUP_SCRIPT = ACTION_DIR / "setup_ansible.sh"
RUN_SCRIPT = ACTION_DIR / "run_ansible_test.sh"
WORKFLOW_FILE = ACTION_ROOT / ".github" / "workflows" / "ansible-test.yml"

INPUT_KEYS = (
    "playbooks-glob",
    "inventory",
    "galaxy-file",
    "requirements-file",
    "ansible-core-version",
    "ansible-lint-version",
    "yamllint-version",
    "run-lint",
    "cache",
)


def _write_exec(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


def _py_minor() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _make_mock_venv(tmp_path: Path, *, empty_tarball: bool = False) -> tuple[Path, Path]:
    """Create a mock venv bin dir with logging ansible-* and lint binaries."""
    venv = tmp_path / "venv"
    bindir = venv / "bin"
    bindir.mkdir(parents=True)
    log = tmp_path / "calls.log"
    _write_exec(bindir / "python", 'exec python3 "$@"\n')
    for name in ("ansible-playbook", "ansible-lint", "yamllint"):
        _write_exec(bindir / name, f'echo "{name} $*" >> "{log}"\nexit 0\n')
    tar_touch = "" if empty_tarball else '  touch "$out/ns-coll-1.0.0.tar.gz"\n'
    _write_exec(
        bindir / "ansible-galaxy",
        f'echo "ansible-galaxy $*" >> "{log}"\n'
        'if [ "$2" = "build" ]; then\n'
        '  out=""\n'
        '  while [ "$#" -gt 0 ]; do\n'
        '    if [ "$1" = "--output-path" ]; then out="$2"; fi\n'
        "    shift\n"
        "  done\n"
        f"{tar_touch}"
        "fi\n"
        "exit 0\n",
    )
    return venv, log


def _run_script(tmp_path: Path, venv: Path, extra_env: dict[str, str]):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path / "home"),
        "ANSIBLE_VENV_DIR": str(venv),
        "ANSIBLE_TEST_COLLECTIONS_DIR": str(tmp_path / "cached-collections"),
    }
    env.update(extra_env)
    return subprocess.run(
        ["bash", str(RUN_SCRIPT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _make_project(tmp_path: Path, *, deps: dict[str, str] | None = None) -> None:
    (tmp_path / "playbooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests").mkdir(parents=True, exist_ok=True)
    (tmp_path / "playbooks" / "a.yml").write_text("---\n")
    (tmp_path / "playbooks" / "b.yml").write_text("---\n")
    (tmp_path / "tests" / "smoke-playbook.yml").write_text("---\n")
    (tmp_path / "tests" / "inventory.ini").write_text("[all]\n")
    galaxy_data: dict[str, object] = {"namespace": "ns", "name": "coll"}
    if deps is not None:
        galaxy_data["dependencies"] = deps
    (tmp_path / "galaxy.yml").write_text(yaml.safe_dump(galaxy_data))


def test_action_and_workflow_valid_and_defaults_match():
    assert ACTION_FILE.is_file()
    assert WORKFLOW_FILE.is_file()

    action_data = yaml.safe_load(ACTION_FILE.read_text(encoding="utf-8"))
    assert action_data["runs"]["using"] == "composite"
    for key in INPUT_KEYS:
        assert key in action_data["inputs"]

    wf_data = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    assert wf_data["permissions"] == {"contents": "read"}
    assert "concurrency" in wf_data
    assert "workflow_call" in wf_data["on"]
    wf_inputs = wf_data["on"]["workflow_call"]["inputs"]
    for key in INPUT_KEYS:
        assert key in wf_inputs
    assert wf_inputs["run-lint"]["type"] == "boolean"
    assert wf_inputs["cache"]["type"] == "boolean"

    for key in (
        "ansible-core-version",
        "ansible-lint-version",
        "yamllint-version",
    ):
        assert action_data["inputs"][key]["default"] == wf_inputs[key]["default"]

    setup_text = SETUP_SCRIPT.read_text(encoding="utf-8")
    assert action_data["inputs"]["ansible-core-version"]["default"] in setup_text
    assert action_data["inputs"]["ansible-lint-version"]["default"] in setup_text
    assert action_data["inputs"]["yamllint-version"]["default"] in setup_text


def test_scripts_are_executable():
    assert os.access(SETUP_SCRIPT, os.X_OK)
    assert os.access(RUN_SCRIPT, os.X_OK)


def test_setup_skips_reinstall_when_marker_matches(tmp_path):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    for name in ("ansible-playbook", "ansible-galaxy"):
        _write_exec(venv / "bin" / name, "exit 0\n")
    (venv / ".installed-spec").write_text(f"py{_py_minor()} ansible-core==9.9.9")

    res = subprocess.run(
        ["bash", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "ANSIBLE_VENV_DIR": str(venv),
            "ANSIBLE_CORE_VERSION": "9.9.9",
            "RUN_LINT": "false",
        },
    )
    assert res.returncode == 0, res.stderr
    assert "already installed" in res.stdout


def test_setup_reinstalls_when_binary_missing_despite_marker(tmp_path):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    _write_exec(venv / "bin" / "ansible-playbook", "exit 0\n")
    # Missing ansible-galaxy binary should trigger reinstall.
    (venv / ".installed-spec").write_text(f"py{_py_minor()} ansible-core==9.9.9")

    mock_bin = tmp_path / "mockbin"
    mock_bin.mkdir()
    log = tmp_path / "install.log"
    _write_exec(mock_bin / "python3", f'echo "{_py_minor()}"')
    _write_exec(mock_bin / "uv", f'echo "uv $*" >> "{log}"\nexit 0\n')

    res = subprocess.run(
        ["bash", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
            "HOME": str(tmp_path),
            "ANSIBLE_VENV_DIR": str(venv),
            "ANSIBLE_CORE_VERSION": "9.9.9",
            "RUN_LINT": "false",
        },
    )
    assert res.returncode == 0, res.stderr
    assert "ansible-core==9.9.9" in log.read_text()


def test_setup_reinstalls_with_clear_and_pip_fallback(tmp_path):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    for name in ("ansible-playbook", "ansible-galaxy"):
        _write_exec(venv / "bin" / name, "exit 0\n")
    (venv / ".installed-spec").write_text("py3.0 ansible-core==1.0.0")

    mock_bin = tmp_path / "mockbin"
    mock_bin.mkdir()
    venv_log = tmp_path / "venv.log"
    pip_log = tmp_path / "pip.log"
    # Mock python3 without uv in PATH to exercise pip fallback and --clear.
    _write_exec(
        mock_bin / "python3",
        f'if [ "$1" = "-m" ]; then echo "python3 $*" >> "{venv_log}"; exit 0; fi\n'
        f'echo "{_py_minor()}"\n',
    )
    _write_exec(venv / "bin" / "pip", f'echo "pip $*" >> "{pip_log}"\nexit 0\n')

    res = subprocess.run(
        ["bash", str(SETUP_SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:/usr/bin:/bin",
            "HOME": str(tmp_path),
            "ANSIBLE_VENV_DIR": str(venv),
            "ANSIBLE_CORE_VERSION": "2.0.0",
            "ANSIBLE_LINT_VERSION": "3.0.0",
            "YAMLLINT_VERSION": "4.0.0",
            "RUN_LINT": "true",
        },
    )
    assert res.returncode == 0, res.stderr
    assert f"python3 -m venv --clear {venv}" in venv_log.read_text()
    installed = pip_log.read_text()
    assert "ansible-core==2.0.0" in installed
    assert "ansible-lint==3.0.0" in installed
    assert "yamllint==4.0.0" in installed
    assert (venv / ".installed-spec").read_text() == (
        f"py{_py_minor()} ansible-core==2.0.0 ansible-lint==3.0.0 yamllint==4.0.0"
    )


def test_run_collection_mode_isolates_local_install_and_upgrades_deps(tmp_path):
    _make_project(tmp_path, deps={"ansible.posix": ">=1.5.0"})
    (tmp_path / "requirements.yml").write_text("collections: []\n")
    venv, log = _make_mock_venv(tmp_path)

    res = _run_script(
        tmp_path,
        venv,
        {
            "PLAYBOOKS_GLOB": "playbooks/*.yml\ntests/*playbook*.yml playbooks/a.yml",
            "INVENTORY": "tests/inventory.ini",
            "GALAXY_FILE": "galaxy.yml",
            "REQUIREMENTS_FILE": "requirements.yml",
            "RUN_LINT": "false",
        },
    )
    assert res.returncode == 0, res.stderr
    lines = log.read_text().splitlines()
    cached_dir = str(tmp_path / "cached-collections")
    # External deps go to cached dir with --upgrade; local tarball uses --no-deps into temp dir.
    assert any(
        line.startswith("ansible-galaxy collection install --upgrade -r ")
        and f" -p {cached_dir}" in line
        and "galaxy-deps.yml" in line
        for line in lines
    )
    assert any(
        line.startswith("ansible-galaxy collection install --no-deps --force ")
        and f" -p {cached_dir}" not in line
        for line in lines
    )
    assert (
        f"ansible-galaxy collection install --upgrade -r requirements.yml -p {cached_dir}" in lines
    )
    assert any(line.startswith("ansible-galaxy collection build") for line in lines)
    checks = [line for line in lines if line.startswith("ansible-playbook")]
    assert checks == [
        "ansible-playbook -i tests/inventory.ini playbooks/a.yml --syntax-check",
        "ansible-playbook -i tests/inventory.ini playbooks/b.yml --syntax-check",
        "ansible-playbook -i tests/inventory.ini tests/smoke-playbook.yml --syntax-check",
    ]
    assert not any(line.startswith(("yamllint", "ansible-lint")) for line in lines)


def test_run_collection_in_subdirectory(tmp_path):
    sub = tmp_path / "collection"
    _make_project(sub)
    venv, log = _make_mock_venv(tmp_path)

    res = _run_script(
        tmp_path,
        venv,
        {
            "PLAYBOOKS_GLOB": "collection/playbooks/*.yml",
            "INVENTORY": "collection/tests/inventory.ini",
            "GALAXY_FILE": "collection/galaxy.yml",
            "REQUIREMENTS_FILE": "",
        },
    )
    assert res.returncode == 0, res.stderr
    lines = log.read_text().splitlines()
    assert any(
        line.startswith("ansible-galaxy collection build --force --output-path")
        and line.endswith(" collection")
        for line in lines
    )


def test_run_fails_when_collection_build_produces_no_tarball(tmp_path):
    _make_project(tmp_path)
    venv, _ = _make_mock_venv(tmp_path, empty_tarball=True)

    res = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/*.yml", "GALAXY_FILE": "galaxy.yml"},
    )
    assert res.returncode == 1
    assert "produced no tarball" in res.stderr


def test_run_consumer_mode_installs_requirements_with_upgrade(tmp_path):
    _make_project(tmp_path)
    (tmp_path / "galaxy.yml").unlink()
    (tmp_path / "requirements.yml").write_text("collections: []\n")
    venv, log = _make_mock_venv(tmp_path)

    res = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/*.yml", "INVENTORY": "tests/inventory.ini"},
    )
    assert res.returncode == 0, res.stderr
    lines = log.read_text().splitlines()
    assert not any("collection build" in line for line in lines)
    assert any(
        line.startswith("ansible-galaxy collection install --upgrade -r requirements.yml")
        for line in lines
    )


def test_run_lint_invokes_and_propagates_failures(tmp_path):
    _make_project(tmp_path)
    venv, log = _make_mock_venv(tmp_path)

    res = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/*.yml", "GALAXY_FILE": "", "RUN_LINT": "true"},
    )
    assert res.returncode == 0, res.stderr
    lines = log.read_text().splitlines()
    assert "yamllint ." in lines
    assert "ansible-lint " in lines or "ansible-lint" in lines

    _write_exec(venv / "bin" / "ansible-lint", "exit 3\n")
    res_lint = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/*.yml", "GALAXY_FILE": "", "RUN_LINT": "true"},
    )
    assert res_lint.returncode == 3

    _write_exec(venv / "bin" / "yamllint", "exit 2\n")
    res_yaml = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/*.yml", "GALAXY_FILE": "", "RUN_LINT": "true"},
    )
    assert res_yaml.returncode == 2


def test_run_empty_inventory_omits_i_flag(tmp_path):
    _make_project(tmp_path)
    venv, log = _make_mock_venv(tmp_path)

    res = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/a.yml", "INVENTORY": "", "GALAXY_FILE": ""},
    )
    assert res.returncode == 0, res.stderr
    assert "ansible-playbook playbooks/a.yml --syntax-check" in log.read_text().splitlines()


def test_run_fails_when_inventory_missing(tmp_path):
    _make_project(tmp_path)
    venv, _ = _make_mock_venv(tmp_path)

    res = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/*.yml", "INVENTORY": "nope.ini", "GALAXY_FILE": ""},
    )
    assert res.returncode == 1
    assert "Inventory file not found" in res.stderr


def test_run_fails_when_no_playbooks_match(tmp_path):
    _make_project(tmp_path)
    venv, _ = _make_mock_venv(tmp_path)

    res = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "nothing/*.yml", "GALAXY_FILE": ""},
    )
    assert res.returncode == 1
    assert "No playbooks found" in res.stderr


def test_run_propagates_syntax_check_failure(tmp_path):
    _make_project(tmp_path)
    venv, _ = _make_mock_venv(tmp_path)
    _write_exec(venv / "bin" / "ansible-playbook", "exit 4\n")

    res = _run_script(
        tmp_path,
        venv,
        {"PLAYBOOKS_GLOB": "playbooks/*.yml", "GALAXY_FILE": ""},
    )
    assert res.returncode == 4
