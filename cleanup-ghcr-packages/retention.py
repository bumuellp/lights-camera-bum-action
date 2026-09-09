"""Retention policy evaluation for container package versions."""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class RetentionAction(StrEnum):
    """Categorization of retention decision for a package version."""

    KEEP_SEMVER = "KEEP-SEMVER"
    KEEP_ACTIVE = "KEEP-ACTIVE"
    KEEP_RECENT_SHA = "KEEP-RECENT-SHA"
    KEEP_CHILD_MANIFEST = "KEEP-CHILD-MANIFEST"
    KEEP_RECENT_UNTAGGED = "KEEP-RECENT-UNTAGGED"
    DELETE = "DELETE"


def parse_packages(raw_packages: str, root_dir: str = ".") -> list[str]:
    """Parse comma-separated, space-separated, or JSON list of package names."""
    raw_packages = raw_packages.strip()
    if not raw_packages or raw_packages == "auto":
        images_dir = os.path.join(root_dir, "images")
        if os.path.isdir(images_dir):
            return [
                d
                for d in sorted(os.listdir(images_dir))
                if os.path.isfile(os.path.join(images_dir, d, "Dockerfile"))
            ]
        return []

    if raw_packages.startswith("["):
        try:
            parsed = json.loads(raw_packages)
            result = []
            for item in parsed:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict) and "name" in item:
                    result.append(item["name"])
            return result
        except json.JSONDecodeError:
            pass

    return [p.strip() for p in raw_packages.replace(",", " ").split() if p.strip()]


def is_semver_release(tags: list[str]) -> bool:
    """Check if any tag matches exact SemVer release (e.g. v1.0.0, 1.2.3)."""
    pattern = re.compile(r"^v?[0-9]+\.[0-9]+\.[0-9]+$")
    return any(pattern.match(t) for t in tags)


def is_active_floating(tags: list[str]) -> bool:
    """Check if tag contains floating release branches (:latest, :v1, :v2, :v1.2)."""
    floating_pattern = re.compile(r"^(latest|v?[0-9]+|v?[0-9]+\.[0-9]+)$")
    return any(floating_pattern.match(t) for t in tags)


def parse_iso_datetime(dt_str: str) -> datetime | None:
    """Parse ISO 8601 datetime string from GitHub API."""
    if not dt_str:
        return None
    try:
        # Handle 'Z' suffix
        cleaned = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except Exception:
        return None


class RetentionPolicy:
    """Evaluates package versions against retention rules."""

    def __init__(
        self,
        keep_sha_count: int = 5,
        untagged_retention_days: int = 7,
        now: datetime | None = None,
    ):
        self.keep_sha_count = keep_sha_count
        self.untagged_retention_days = untagged_retention_days
        self._now = now or datetime.now(UTC)

    def evaluate(
        self,
        versions: list[dict[str, Any]],
        referenced_digests: set[str] | None = None,
    ) -> list[tuple[dict[str, Any], RetentionAction, str]]:
        """Evaluate each version and return a list of (version, action, explanation).

        Versions are evaluated newest to oldest.
        """
        referenced_digests = referenced_digests or set()
        sorted_versions = sorted(
            versions,
            key=lambda v: v.get("created_at", ""),
            reverse=True,
        )

        decisions: list[tuple[dict[str, Any], RetentionAction, str]] = []
        kept_sha_count = 0
        grace_cutoff = self._now - timedelta(days=self.untagged_retention_days)

        for v in sorted_versions:
            tags = v.get("metadata", {}).get("container", {}).get("tags", [])
            digest_name = v.get("name", "")
            created_at_str = v.get("created_at", "")
            created_at = parse_iso_datetime(created_at_str)

            # 1. ALWAYS PRESERVE SemVer Release checkpoints (e.g. v1.0.0)
            if is_semver_release(tags):
                decisions.append(
                    (
                        v,
                        RetentionAction.KEEP_SEMVER,
                        f"SemVer release tags: {tags}",
                    )
                )
                continue

            # 2. ALWAYS PRESERVE Active Floating tags (:latest, :v1)
            if is_active_floating(tags):
                decisions.append(
                    (
                        v,
                        RetentionAction.KEEP_ACTIVE,
                        f"Active floating tags: {tags}",
                    )
                )
                continue

            # 3. Retain the most recent N commit SHA versions
            if tags and kept_sha_count < self.keep_sha_count:
                kept_sha_count += 1
                decisions.append(
                    (
                        v,
                        RetentionAction.KEEP_RECENT_SHA,
                        f"Recent commit SHA tag ({kept_sha_count}/{self.keep_sha_count}): {tags}",
                    )
                )
                continue

            # 4. Handle untagged versions (tags == [])
            if not tags:
                # Layer 1: Child manifest referenced by an active tagged index
                if digest_name and digest_name in referenced_digests:
                    decisions.append(
                        (
                            v,
                            RetentionAction.KEEP_CHILD_MANIFEST,
                            f"Active child manifest referenced by index: {digest_name}",
                        )
                    )
                    continue

                # Layer 2: Age-based grace period (default 7 days)
                if created_at and created_at >= grace_cutoff:
                    decisions.append(
                        (
                            v,
                            RetentionAction.KEEP_RECENT_UNTAGGED,
                            f"Recent untagged version within {self.untagged_retention_days}d grace period ({created_at_str})",
                        )
                    )
                    continue

                # Expired and unreferenced untagged version
                decisions.append(
                    (
                        v,
                        RetentionAction.DELETE,
                        f"Orphaned untagged version older than {self.untagged_retention_days} days",
                    )
                )
                continue

            # 5. Older SHA version beyond keep_sha_count
            decisions.append(
                (
                    v,
                    RetentionAction.DELETE,
                    f"Older commit SHA tag exceeding retention count ({self.keep_sha_count}): {tags}",
                )
            )

        return decisions
