#!/usr/bin/env python3
"""Clean up orphaned and stale container package versions from GHCR."""

from __future__ import annotations

import os

from github_client import GitHubPackagesClient
from retention import (
    RetentionAction,
    RetentionPolicy,
    is_active_floating,
    is_semver_release,
    parse_packages,
)


def cleanup_package(
    client: GitHubPackagesClient,
    policy: RetentionPolicy,
    package_name: str,
    dry_run: bool = False,
) -> dict[str, int]:
    """Evaluate and clean up package versions for a single container package."""
    versions = client.get_package_versions(package_name)
    if not versions:
        print(f"[{package_name}] No versions found or unable to access package.")
        return {"kept": 0, "deleted": 0}

    print(f"\n--- Processing {package_name} ({len(versions)} total versions) ---")

    # 1. Discover all active tags (SemVer, floating, recent SHAs) to query OCI Index child manifests
    referenced_digests: set[str] = set()
    active_tags_to_check: set[str] = set()

    for v in versions:
        tags = v.get("metadata", {}).get("container", {}).get("tags", [])
        for tag in tags:
            if is_semver_release([tag]) or is_active_floating([tag]):
                active_tags_to_check.add(tag)

    # Always check 'latest' if present
    active_tags_to_check.add("latest")

    for tag in active_tags_to_check:
        child_digests = client.get_index_child_digests(package_name, tag)
        if child_digests:
            referenced_digests.update(child_digests)

    if referenced_digests:
        print(
            f"  [DISCOVERY] Identified {len(referenced_digests)} active child manifest digests protected from deletion."
        )

    # 2. Evaluate retention decisions
    decisions = policy.evaluate(versions, referenced_digests=referenced_digests)

    kept = 0
    deleted = 0

    for v, action, reason in decisions:
        vid = v.get("id")
        created_at = v.get("created_at", "")
        tags = v.get("metadata", {}).get("container", {}).get("tags", [])

        if action == RetentionAction.DELETE:
            display_action = "[DRY-RUN DELETE]" if dry_run else "[DELETE]"
            print(f"  {display_action} ID {vid} ({created_at}) tags: {tags} - {reason}")
            if not dry_run:
                if client.delete_package_version(package_name, vid):
                    deleted += 1
            else:
                deleted += 1
        else:
            print(f"  [{action.value}] ID {vid} ({created_at}) tags: {tags} - {reason}")
            kept += 1

    return {"kept": kept, "deleted": deleted}


def main() -> None:
    raw_packages = os.environ.get("INPUT_PACKAGE_NAMES", "auto")
    owner = os.environ.get("INPUT_REPOSITORY_OWNER") or os.environ.get(
        "GITHUB_REPOSITORY_OWNER", ""
    )
    token = (
        os.environ.get("INPUT_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN", "")
    )
    keep_sha_count = int(os.environ.get("INPUT_KEEP_SHA_COUNT", "5"))
    untagged_retention_days = int(os.environ.get("INPUT_UNTAGGED_RETENTION_DAYS", "7"))
    dry_run = os.environ.get("INPUT_DRY_RUN", "false").lower() in ("true", "1")

    packages = parse_packages(raw_packages)
    if not packages:
        print("No packages found or specified to clean.")
        return

    client = GitHubPackagesClient(token=token, owner=owner)
    policy = RetentionPolicy(
        keep_sha_count=keep_sha_count,
        untagged_retention_days=untagged_retention_days,
    )

    total_kept = 0
    total_deleted = 0

    for pkg in packages:
        stats = cleanup_package(
            client=client,
            policy=policy,
            package_name=pkg,
            dry_run=dry_run,
        )
        total_kept += stats["kept"]
        total_deleted += stats["deleted"]

    print(f"\nCleanup complete. Kept: {total_kept}, Deleted: {total_deleted}")


if __name__ == "__main__":
    main()
