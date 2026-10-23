"""Unit and edge-case tests for common/yaml-common.sh and parse-config."""

import json
import os
import subprocess
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
YAML_COMMON_SH = ACTION_ROOT / "common" / "yaml-common.sh"
PARSE_SH = ACTION_ROOT / "parse-config" / "parse.sh"


def run_filter_json(
    json_input: str, keys: str = "", mask: str = "false"
) -> subprocess.CompletedProcess:
    """Helper to run filter_json_keys inside a bash subshell."""
    escaped_json = json_input.replace("'", "'\\''")
    escaped_keys = keys.replace("'", "'\\''")
    cmd = (
        f"source '{YAML_COMMON_SH}' && filter_json_keys '{escaped_json}' '{escaped_keys}' '{mask}'"
    )
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, check=False)


def test_empty_or_whitespace_input():
    # Empty string
    res = run_filter_json("")
    assert res.returncode == 0
    assert res.stdout.strip() == "{}"

    # Empty object
    res = run_filter_json("{}")
    assert res.returncode == 0
    assert res.stdout.strip() == "{}"


def test_no_keys_returns_original_json():
    # When keys parameter is empty, the entire JSON document is returned
    doc = {"name": "test", "active": True}
    res = run_filter_json(json.dumps(doc), keys="")
    assert res.returncode == 0
    assert json.loads(res.stdout.strip()) == doc


def test_whitespace_or_delimiter_only_keys():
    # When keys is only commas, spaces, or tabs
    doc = {"a": "val"}
    res = run_filter_json(json.dumps(doc), keys="   , \t\n  ,  ")
    assert res.returncode == 0
    assert res.stdout.strip() == "{}"


def test_missing_and_null_keys():
    doc = {
        "existing": "here",
        "nullable": None,
    }
    res = run_filter_json(json.dumps(doc), keys="non_existent, nullable, existing")
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())
    assert "non_existent" not in data
    assert "nullable" not in data
    assert data["existing"] == "here"


def test_data_types_representation():
    doc = {
        "bool_true": True,
        "bool_false": False,
        "int_val": 42,
        "float_val": 3.1415,
        "empty_list": [],
        "list_val": ["alpha", 123, False],
        "nested_obj": {"child": "leaf", "count": 10},
    }
    keys = "bool_true, bool_false, int_val, float_val, empty_list, list_val, nested_obj"
    res = run_filter_json(json.dumps(doc), keys=keys)
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())

    assert data["bool_true"] == "true"
    assert data["bool_false"] == "false"
    assert data["int_val"] == "42"
    assert data["float_val"] == "3.1415"
    assert data["empty_list"] == ""
    assert data["list_val"] == "alpha,123,false"

    nested_parsed = json.loads(data["nested_obj"])
    assert nested_parsed == {"child": "leaf", "count": 10}


def test_nested_dot_paths():
    doc = {
        "server": {
            "node": {
                "location": "fsn1",
                "cores": 4,
            }
        },
        "discord": {
            "allowed_user_ids": ["111222", "333444"],
        },
    }
    keys = "server.node.location, discord.allowed_user_ids"
    res = run_filter_json(json.dumps(doc), keys=keys)
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())

    assert data["server.node.location"] == "fsn1"
    assert data["discord.allowed_user_ids"] == "111222,333444"
    assert "server_node_location" not in data
    assert "discord_allowed_user_ids" not in data


def test_masking_behavior():
    doc = {"secret_token": "super_secret_123", "public_id": "public_999"}

    # Masking enabled: stderr must contain ::add-mask:: for extracted secrets
    res_masked = run_filter_json(json.dumps(doc), keys="secret_token", mask="true")
    assert res_masked.returncode == 0
    assert "::add-mask::super_secret_123" in res_masked.stderr

    # Masking disabled: stderr must NOT contain ::add-mask::
    res_unmasked = run_filter_json(json.dumps(doc), keys="secret_token", mask="false")
    assert res_unmasked.returncode == 0
    assert "::add-mask::" not in res_unmasked.stderr


def test_delimiters_variations():
    doc = {"k1": "v1", "k2": "v2", "k3": "v3"}
    # Multiline with irregular spaces, tabs, and commas
    keys = "k1,\n   k2  \t,\n\n  k3  "
    res = run_filter_json(json.dumps(doc), keys=keys)
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())
    assert data == {"k1": "v1", "k2": "v2", "k3": "v3"}


def test_parse_sh_missing_both_files(tmp_path):
    gh_output = tmp_path / "github_output"
    gh_output.touch()

    env = {
        "PATH": os.environ.get("PATH", ""),
        "CONFIG_FILE": str(tmp_path / "nonexistent1.yaml"),
        "FALLBACK_FILE": str(tmp_path / "nonexistent2.yaml"),
        "KEYS": "some_key",
        "GITHUB_OUTPUT": str(gh_output),
    }
    res = subprocess.run([str(PARSE_SH)], env=env, capture_output=True, text=True, check=False)
    assert res.returncode == 0
    assert "Neither" in res.stdout
    assert "json={}" in gh_output.read_text()


def test_parse_sh_fallback_mechanism(tmp_path):
    gh_output = tmp_path / "github_output"
    gh_output.touch()

    fallback = tmp_path / "settings.example.yaml"
    fallback.write_text("discord:\n  enabled: false\n  allowed_user_ids: []\n")

    env = {
        "PATH": os.environ.get("PATH", ""),
        "CONFIG_FILE": str(tmp_path / "missing.yaml"),
        "FALLBACK_FILE": str(fallback),
        "KEYS": "discord.enabled, discord.allowed_user_ids",
        "GITHUB_OUTPUT": str(gh_output),
    }
    res = subprocess.run([str(PARSE_SH)], env=env, capture_output=True, text=True, check=False)
    assert res.returncode == 0

    output_lines = gh_output.read_text().splitlines()
    json_lines = [line for line in output_lines if line.startswith("json=")]
    assert len(json_lines) == 1
    data = json.loads(json_lines[0].removeprefix("json="))
    assert data["discord.enabled"] == "false"
    assert data["discord.allowed_user_ids"] == ""
