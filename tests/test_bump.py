"""Unit tests for bump-version/bump.py."""

from pathlib import Path
import sys
import pytest

ACTION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ACTION_ROOT / "bump-version"))

from bump import parse_semver, determine_bump_type, calculate_next_version


def test_parse_semver_valid_and_invalid():
    assert parse_semver("v1.2.3") == (1, 2, 3)
    assert parse_semver("1.2.3") == (1, 2, 3)
    assert parse_semver("v10.200.30") == (10, 200, 30)
    assert parse_semver("v1") is None
    assert parse_semver("latest") is None
    assert parse_semver("v1.2") is None


def test_determine_bump_type_patch():
    commits = ["fix(cli): fix parsing error", "chore: update deps"]
    assert determine_bump_type(commits) == "patch"


def test_determine_bump_type_minor():
    commits = ["feat(images): add new container image", "fix: small bug"]
    assert determine_bump_type(commits) == "minor"


def test_determine_bump_type_major():
    commits = ["feat!: break old api structure", "fix: small bug"]
    assert determine_bump_type(commits) == "major"

    commits_body = ["chore: update", "BREAKING CHANGE: remove deprecated endpoints"]
    assert determine_bump_type(commits_body) == "major"


def test_calculate_next_version_from_scratch():
    next_tag, major, minor = calculate_next_version(None, "patch")
    assert next_tag == "v1.0.0"
    assert major == "v1"
    assert minor == "v1.0"


def test_calculate_next_version_increments():
    # Patch
    next_tag, major, minor = calculate_next_version("v1.0.0", "patch")
    assert next_tag == "v1.0.1"
    assert major == "v1"
    assert minor == "v1.0"

    # Minor
    next_tag, major, minor = calculate_next_version("v1.0.1", "minor")
    assert next_tag == "v1.1.0"
    assert major == "v1"
    assert minor == "v1.1"

    # Major
    next_tag, major, minor = calculate_next_version("v1.1.0", "major")
    assert next_tag == "v2.0.0"
    assert major == "v2"
    assert minor == "v2.0"
