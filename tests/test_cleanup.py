"""Unit tests for cleanup-ghcr-packages/cleanup.py."""

from pathlib import Path
import sys
import pytest

ACTION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ACTION_ROOT / "cleanup-ghcr-packages"))

from cleanup import parse_packages, is_semver_release, is_active_floating


def test_parse_packages_formats():
    assert parse_packages("app1, app2, app3") == ["app1", "app2", "app3"]
    assert parse_packages("app1 app2") == ["app1", "app2"]
    assert parse_packages('["app1", "app2"]') == ["app1", "app2"]
    assert parse_packages('[{"name": "app1"}, {"name": "app2"}]') == ["app1", "app2"]


def test_is_semver_release():
    assert is_semver_release(["v1.0.0"]) is True
    assert is_semver_release(["1.2.3"]) is True
    assert is_semver_release(["v2.10.4", "latest"]) is True
    assert is_semver_release(["v1"]) is False
    assert is_semver_release(["latest"]) is False
    assert is_semver_release(["abc123456789"]) is False
    assert is_semver_release([]) is False


def test_is_active_floating():
    assert is_active_floating(["latest"]) is True
    assert is_active_floating(["v1"]) is True
    assert is_active_floating(["v2"]) is True
    assert is_active_floating(["v1.2"]) is True
    assert is_active_floating(["abc123456789"]) is False
    assert is_active_floating([]) is False
