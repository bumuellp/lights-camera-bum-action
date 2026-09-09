"""Comprehensive unit tests for cleanup-ghcr-packages."""

import sys
from datetime import UTC, datetime
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ACTION_ROOT / "cleanup-ghcr-packages"))

from cleanup import cleanup_package
from retention import (
    RetentionAction,
    RetentionPolicy,
    is_active_floating,
    is_semver_release,
    parse_packages,
)


def test_parse_packages_formats(tmp_path):
    assert parse_packages("app1, app2, app3") == ["app1", "app2", "app3"]
    assert parse_packages("app1 app2") == ["app1", "app2"]
    assert parse_packages('["app1", "app2"]') == ["app1", "app2"]
    assert parse_packages('[{"name": "app1"}, {"name": "app2"}]') == ["app1", "app2"]

    # Test auto discovery
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "tool-a").mkdir()
    (images_dir / "tool-a" / "Dockerfile").touch()
    (images_dir / "tool-b").mkdir()
    (images_dir / "tool-b" / "Dockerfile").touch()
    (images_dir / "ignored-dir").mkdir()  # no Dockerfile

    discovered = parse_packages("auto", root_dir=str(tmp_path))
    assert discovered == ["tool-a", "tool-b"]


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


def test_retention_policy_rules():
    fixed_now = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
    policy = RetentionPolicy(
        keep_sha_count=2,
        untagged_retention_days=7,
        now=fixed_now,
    )

    sample_versions = [
        # 1. SemVer release (must keep)
        {
            "id": 101,
            "name": "sha256:index101",
            "created_at": "2026-09-08T10:00:00Z",
            "metadata": {"container": {"tags": ["v1.0.0"]}},
        },
        # 2. Active floating tag (must keep)
        {
            "id": 102,
            "name": "sha256:index102",
            "created_at": "2026-09-08T09:00:00Z",
            "metadata": {"container": {"tags": ["latest", "v1"]}},
        },
        # 3. Recent commit SHA #1 (must keep, count 1/2)
        {
            "id": 103,
            "name": "sha256:sha103",
            "created_at": "2026-09-08T08:00:00Z",
            "metadata": {"container": {"tags": ["commitsha1"]}},
        },
        # 4. Recent commit SHA #2 (must keep, count 2/2)
        {
            "id": 104,
            "name": "sha256:sha104",
            "created_at": "2026-09-07T08:00:00Z",
            "metadata": {"container": {"tags": ["commitsha2"]}},
        },
        # 5. Older commit SHA #3 (must delete, exceeds count of 2)
        {
            "id": 105,
            "name": "sha256:sha105",
            "created_at": "2026-09-06T08:00:00Z",
            "metadata": {"container": {"tags": ["commitsha3"]}},
        },
        # 6. Untagged child manifest referenced by active index (must keep)
        {
            "id": 106,
            "name": "sha256:child_amd64",
            "created_at": "2026-08-01T00:00:00Z",  # older than 7d, but referenced!
            "metadata": {"container": {"tags": []}},
        },
        # 7. Untagged version within 7-day grace period (must keep)
        {
            "id": 107,
            "name": "sha256:recent_unreferenced",
            "created_at": "2026-09-05T00:00:00Z",  # 3 days old (< 7d)
            "metadata": {"container": {"tags": []}},
        },
        # 8. Untagged version older than 7-day grace period & unreferenced (must delete)
        {
            "id": 108,
            "name": "sha256:old_abandoned",
            "created_at": "2026-08-20T00:00:00Z",  # 19 days old (> 7d)
            "metadata": {"container": {"tags": []}},
        },
    ]

    referenced_digests = {"sha256:child_amd64"}
    decisions = policy.evaluate(sample_versions, referenced_digests=referenced_digests)

    results_by_id = {v["id"]: action for v, action, _ in decisions}

    assert results_by_id[101] == RetentionAction.KEEP_SEMVER
    assert results_by_id[102] == RetentionAction.KEEP_ACTIVE
    assert results_by_id[103] == RetentionAction.KEEP_RECENT_SHA
    assert results_by_id[104] == RetentionAction.KEEP_RECENT_SHA
    assert results_by_id[105] == RetentionAction.DELETE
    assert results_by_id[106] == RetentionAction.KEEP_CHILD_MANIFEST
    assert results_by_id[107] == RetentionAction.KEEP_RECENT_UNTAGGED
    assert results_by_id[108] == RetentionAction.DELETE


class DummyClient:
    """Mock client for testing cleanup_package flow."""

    def __init__(self, versions, child_digests):
        self._versions = versions
        self._child_digests = child_digests
        self.deleted_ids = []

    def get_package_versions(self, package_name: str):
        return self._versions

    def get_index_child_digests(self, package_name: str, reference: str):
        return self._child_digests.get(reference, set())

    def delete_package_version(self, package_name: str, version_id: int):
        self.deleted_ids.append(version_id)
        return True


def test_cleanup_package_dry_run_vs_live():
    fixed_now = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)
    policy = RetentionPolicy(
        keep_sha_count=1,
        untagged_retention_days=7,
        now=fixed_now,
    )

    versions = [
        {
            "id": 1,
            "name": "sha256:index_latest",
            "created_at": "2026-09-08T10:00:00Z",
            "metadata": {"container": {"tags": ["latest"]}},
        },
        {
            "id": 2,
            "name": "sha256:child_active",
            "created_at": "2026-08-01T00:00:00Z",
            "metadata": {"container": {"tags": []}},
        },
        {
            "id": 3,
            "name": "sha256:old_orphan",
            "created_at": "2026-08-01T00:00:00Z",
            "metadata": {"container": {"tags": []}},
        },
    ]
    child_digests = {"latest": {"sha256:child_active"}}

    # Test Dry Run
    client_dry = DummyClient(versions, child_digests)
    stats_dry = cleanup_package(client_dry, policy, "test-pkg", dry_run=True)
    assert stats_dry["kept"] == 2
    assert stats_dry["deleted"] == 1
    assert client_dry.deleted_ids == []  # Not actually deleted in dry run

    # Test Live Run
    client_live = DummyClient(versions, child_digests)
    stats_live = cleanup_package(client_live, policy, "test-pkg", dry_run=False)
    assert stats_live["kept"] == 2
    assert stats_live["deleted"] == 1
    assert client_live.deleted_ids == [3]  # ID 3 deleted, ID 2 preserved as child manifest!
