"""Unit tests for build-ghcr-image/compute_tags.sh."""

from pathlib import Path
import subprocess
import pytest

ACTION_ROOT = Path(__file__).resolve().parent.parent
COMPUTE_TAGS_SH = ACTION_ROOT / "build-ghcr-image" / "compute_tags.sh"


def run_compute_tags(registry="ghcr.io", owner="myorg", image="myapp", sha="", extra=""):
    cmd = [str(COMPUTE_TAGS_SH), registry, owner, image, sha, extra]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_compute_tags_default_latest():
    res = run_compute_tags(registry="ghcr.io", owner="bumuellp", image="mcpo", sha="", extra="")
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert tags == ["ghcr.io/bumuellp/mcpo:latest"]


def test_compute_tags_with_sha():
    res = run_compute_tags(registry="ghcr.io", owner="bumuellp", image="mcpo", sha="abc1234", extra="")
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert tags == [
        "ghcr.io/bumuellp/mcpo:latest",
        "ghcr.io/bumuellp/mcpo:abc1234",
    ]


def test_compute_tags_with_extra_tags_comma_separated():
    res = run_compute_tags(
        registry="ghcr.io",
        owner="bumuellp",
        image="mcpo",
        sha="abc1234",
        extra="v1, v1.0.0",
    )
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert tags == [
        "ghcr.io/bumuellp/mcpo:latest",
        "ghcr.io/bumuellp/mcpo:abc1234",
        "ghcr.io/bumuellp/mcpo:v1",
        "ghcr.io/bumuellp/mcpo:v1.0.0",
    ]


def test_compute_tags_custom_registry():
    res = run_compute_tags(
        registry="registry.example.com",
        owner="team",
        image="service",
        sha="def5678",
        extra="release",
    )
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert tags == [
        "registry.example.com/team/service:latest",
        "registry.example.com/team/service:def5678",
        "registry.example.com/team/service:release",
    ]


def test_compute_tags_missing_required_args():
    res = subprocess.run([str(COMPUTE_TAGS_SH)], capture_output=True, text=True, check=False)
    assert res.returncode != 0
