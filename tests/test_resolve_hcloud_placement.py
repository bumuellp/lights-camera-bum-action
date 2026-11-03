"""Unit tests for resolve-hcloud-placement action and resolve.sh script."""

import json
import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "resolve-hcloud-placement"
ACTION_FILE = ACTION_DIR / "action.yml"
RESOLVE_SH = ACTION_DIR / "resolve.sh"


def test_action_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Resolve Hetzner Cloud Placement"
    assert "inputs" in data
    assert "token" in data["inputs"]
    assert data["inputs"]["token"]["required"] is True
    assert "server-types" in data["inputs"]
    assert data["inputs"]["server-types"]["required"] is True
    assert "locations" in data["inputs"]
    assert data["inputs"]["locations"].get("default") == "fsn1"
    assert "strategy" in data["inputs"]
    assert data["inputs"]["strategy"].get("default") == "type-first"
    assert "fail-on-unavailable" in data["inputs"]
    assert data["inputs"]["fail-on-unavailable"].get("default") == "true"

    assert "outputs" in data
    for out in ["server-type", "location", "architecture", "cores", "memory", "available"]:
        assert out in data["outputs"]


def test_resolve_sh_executable():
    assert RESOLVE_SH.is_file(), "resolve.sh must exist"


def test_resolve_sh_missing_token():
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": os.environ.get("PATH", "")},
    )
    assert res.returncode != 0
    assert "token" in res.stderr.lower()


def test_resolve_sh_missing_server_types():
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)],
        capture_output=True,
        text=True,
        check=False,
        env={"HCLOUD_TOKEN": "mock-token", "PATH": os.environ.get("PATH", "")},
    )
    assert res.returncode != 0
    assert "server-types" in res.stderr.lower()


def create_mock_curl(bin_dir: Path, response_body: str, http_code: int = 200) -> Path:
    mock_curl = bin_dir / "curl"
    mock_curl.write_text(f"""#!/usr/bin/env python3
import sys

print('''{response_body}''')
print("{http_code}")
sys.exit(0)
""")
    mock_curl.chmod(0o755)
    return mock_curl


MOCK_CATALOG = json.dumps(
    {
        "server_types": [
            {
                "id": 1,
                "name": "cax21",
                "architecture": "arm",
                "cores": 4,
                "memory": 8,
                "locations": [
                    {"name": "fsn1", "available": False},
                    {"name": "nbg1", "available": True},
                ],
            },
            {
                "id": 2,
                "name": "cax31",
                "architecture": "arm",
                "cores": 8,
                "memory": 16,
                "locations": [
                    {"name": "fsn1", "available": False},
                    {"name": "nbg1", "available": False},
                ],
            },
            {
                "id": 3,
                "name": "cpx32",
                "architecture": "x86",
                "cores": 4,
                "memory": 8,
                "locations": [
                    {"name": "fsn1", "available": True},
                    {"name": "nbg1", "available": True},
                ],
            },
        ]
    }
)


def parse_github_output(output_file: Path) -> dict:
    result = {}
    if not output_file.is_file():
        return result
    for line in output_file.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def test_resolve_sh_api_error(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    create_mock_curl(mock_bin, "Unauthorized", http_code=401)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "bad-token",
        "SERVER_TYPES": "cax21",
        "LOCATIONS": "fsn1",
    }
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode != 0
    assert "401" in res.stderr


def test_resolve_sh_type_first_waterfall(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    create_mock_curl(mock_bin, MOCK_CATALOG)
    output_file = tmp_path / "github_output"

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "valid-token",
        "SERVER_TYPES": "cax21, cax31, cpx32",
        "LOCATIONS": "fsn1",
        "STRATEGY": "type-first",
        "GITHUB_OUTPUT": str(output_file),
    }
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}\n{res.stdout}"
    outputs = parse_github_output(output_file)

    # cax21 is false in fsn1, cax31 is false in fsn1 -> falls back to cpx32
    assert outputs.get("server-type") == "cpx32"
    assert outputs.get("location") == "fsn1"
    assert outputs.get("architecture") == "x86"
    assert outputs.get("cores") == "4"
    assert outputs.get("memory") == "8"
    assert outputs.get("available") == "true"


def test_resolve_sh_location_waterfall(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    create_mock_curl(mock_bin, MOCK_CATALOG)
    output_file = tmp_path / "github_output"

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "valid-token",
        "SERVER_TYPES": "cax21",
        "LOCATIONS": "fsn1, nbg1",
        "STRATEGY": "type-first",
        "GITHUB_OUTPUT": str(output_file),
    }
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0, f"Script failed: {res.stderr}\n{res.stdout}"
    outputs = parse_github_output(output_file)

    # cax21 false in fsn1, but true in nbg1 -> picks nbg1
    assert outputs.get("server-type") == "cax21"
    assert outputs.get("location") == "nbg1"
    assert outputs.get("architecture") == "arm"
    assert outputs.get("available") == "true"


def test_resolve_sh_strategy_difference(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    create_mock_curl(mock_bin, MOCK_CATALOG)

    # With type-first: cax21 in nbg1 wins over cpx32 in fsn1
    out_type = tmp_path / "out_type"
    env_type = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "valid-token",
        "SERVER_TYPES": "cax21, cpx32",
        "LOCATIONS": "fsn1, nbg1",
        "STRATEGY": "type-first",
        "GITHUB_OUTPUT": str(out_type),
    }
    res_type = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env_type
    )
    assert res_type.returncode == 0
    outputs_type = parse_github_output(out_type)
    assert outputs_type.get("server-type") == "cax21"
    assert outputs_type.get("location") == "nbg1"

    # With location-first: fsn1 is prioritized, so cpx32 in fsn1 wins over cax21 in nbg1
    out_loc = tmp_path / "out_loc"
    env_loc = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "valid-token",
        "SERVER_TYPES": "cax21, cpx32",
        "LOCATIONS": "fsn1, nbg1",
        "STRATEGY": "location-first",
        "GITHUB_OUTPUT": str(out_loc),
    }
    res_loc = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env_loc
    )
    assert res_loc.returncode == 0
    outputs_loc = parse_github_output(out_loc)
    assert outputs_loc.get("server-type") == "cpx32"
    assert outputs_loc.get("location") == "fsn1"


def test_resolve_sh_all_unavailable_fail(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    create_mock_curl(mock_bin, MOCK_CATALOG)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "valid-token",
        "SERVER_TYPES": "cax31",
        "LOCATIONS": "fsn1, nbg1",
        "FAIL_ON_UNAVAILABLE": "true",
    }
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode != 0
    assert "no available server placement found" in res.stderr.lower()


def test_resolve_sh_all_unavailable_soft(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    create_mock_curl(mock_bin, MOCK_CATALOG)
    output_file = tmp_path / "github_output"

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "valid-token",
        "SERVER_TYPES": "cax31",
        "LOCATIONS": "fsn1, nbg1",
        "FAIL_ON_UNAVAILABLE": "false",
        "GITHUB_OUTPUT": str(output_file),
    }
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    outputs = parse_github_output(output_file)
    assert outputs.get("server-type") == "cax31"
    assert outputs.get("location") == "fsn1"
    assert outputs.get("available") == "false"


def test_resolve_sh_multiline_and_spaces(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    create_mock_curl(mock_bin, MOCK_CATALOG)
    output_file = tmp_path / "github_output"

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "HCLOUD_TOKEN": "valid-token",
        "SERVER_TYPES": "  cax31 \n cpx32  \n",
        "LOCATIONS": " fsn1   nbg1 ",
        "STRATEGY": "type-first",
        "GITHUB_OUTPUT": str(output_file),
    }
    res = subprocess.run(
        ["bash", str(RESOLVE_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    outputs = parse_github_output(output_file)
    assert outputs.get("server-type") == "cpx32"
    assert outputs.get("location") == "fsn1"
    assert outputs.get("available") == "true"
