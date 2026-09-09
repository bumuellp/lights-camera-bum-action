"""Unit tests for build-ghcr-image/compute_tags.sh."""

import subprocess
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
COMPUTE_TAGS_SH = ACTION_ROOT / "build-ghcr-image" / "compute_tags.sh"


def run_compute_tags(registry="ghcr.io", owner="myorg", image="myapp", sha="", extra=""):
    cmd = [str(COMPUTE_TAGS_SH), registry, owner, image, sha, extra]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_compute_tags_default_latest_and_major():
    res = run_compute_tags(registry="ghcr.io", owner="bumuellp", image="mcpo", sha="", extra="")
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert "ghcr.io/bumuellp/mcpo:latest" in tags
    assert "ghcr.io/bumuellp/mcpo:v1" in tags


def test_compute_tags_with_sha():
    res = run_compute_tags(
        registry="ghcr.io", owner="bumuellp", image="mcpo", sha="abc1234", extra=""
    )
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert "ghcr.io/bumuellp/mcpo:latest" in tags
    assert "ghcr.io/bumuellp/mcpo:abc1234" in tags
    assert "ghcr.io/bumuellp/mcpo:v1" in tags


def test_compute_tags_with_semver_hierarchy_expansion():
    res = run_compute_tags(
        registry="ghcr.io",
        owner="bumuellp",
        image="mcpo",
        sha="abc1234",
        extra="v1.2.3",
    )
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert tags == [
        "ghcr.io/bumuellp/mcpo:latest",
        "ghcr.io/bumuellp/mcpo:abc1234",
        "ghcr.io/bumuellp/mcpo:v1.2.3",
        "ghcr.io/bumuellp/mcpo:v1.2",
        "ghcr.io/bumuellp/mcpo:v1",
    ]


def test_compute_tags_v2_semver():
    res = run_compute_tags(
        registry="ghcr.io",
        owner="bumuellp",
        image="mcpo",
        sha="def5678",
        extra="v2.0.1",
    )
    assert res.returncode == 0
    tags = res.stdout.strip().splitlines()
    assert tags == [
        "ghcr.io/bumuellp/mcpo:latest",
        "ghcr.io/bumuellp/mcpo:def5678",
        "ghcr.io/bumuellp/mcpo:v2.0.1",
        "ghcr.io/bumuellp/mcpo:v2.0",
        "ghcr.io/bumuellp/mcpo:v2",
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
    assert "registry.example.com/team/service:latest" in tags
    assert "registry.example.com/team/service:def5678" in tags
    assert "registry.example.com/team/service:release" in tags


def test_compute_tags_missing_required_args():
    res = subprocess.run([str(COMPUTE_TAGS_SH)], capture_output=True, text=True, check=False)
    assert res.returncode != 0
