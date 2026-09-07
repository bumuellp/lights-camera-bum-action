#!/usr/bin/env python3
"""Calculate next Semantic Version from Conventional Commits since last release tag."""

import json
import os
import re
import subprocess
import sys


def parse_semver(tag: str) -> tuple[int, int, int] | None:
    """Parse tag into (major, minor, patch) integer tuple."""
    match = re.match(r"^v?([0-9]+)\.([0-9]+)\.([0-9]+)$", tag.strip())
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None


def get_latest_semver_tag() -> str | None:
    """Find the highest SemVer release tag in the repository."""
    cmd = ["git", "tag", "-l", "v*.*.*"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            return None
        tags = [t.strip() for t in res.stdout.splitlines() if t.strip()]
    except Exception:
        return None

    semver_tags = []
    for t in tags:
        parsed = parse_semver(t)
        if parsed:
            semver_tags.append((parsed, t))

    if not semver_tags:
        return None

    # Sort by major, minor, patch
    semver_tags.sort(key=lambda x: x[0], reverse=True)
    return semver_tags[0][1]


def get_commits_since_tag(tag: str | None) -> list[str]:
    """Get commit messages since the specified tag, or all commits if None."""
    if tag:
        cmd = ["git", "log", f"{tag}..HEAD", "--format=%B%x00"]
    else:
        cmd = ["git", "log", "--format=%B%x00"]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            return []
        return [c.strip() for c in res.stdout.split("\x00") if c.strip()]
    except Exception:
        return []


def determine_bump_type(commits: list[str]) -> str:
    """Determine bump type (major, minor, patch, or none) from commit messages."""
    if not commits:
        return "none"

    has_breaking = False
    has_feat = False
    has_fix = False

    breaking_pattern = re.compile(r"(BREAKING CHANGE:|^[a-zA-Z0-9_-]+(\([^)]+\))?!:)", re.MULTILINE)
    feat_pattern = re.compile(r"^feat(\([^)]+\))?:", re.MULTILINE)
    fix_pattern = re.compile(r"^(fix|perf|refactor)(\([^)]+\))?:", re.MULTILINE)

    for msg in commits:
        if breaking_pattern.search(msg):
            has_breaking = True
            break
        if feat_pattern.search(msg):
            has_feat = True
        elif fix_pattern.search(msg):
            has_fix = True

    if has_breaking:
        return "major"
    if has_feat:
        return "minor"
    if has_fix:
        return "patch"
    return "patch"


def calculate_next_version(
    current_tag: str | None,
    bump_type: str,
) -> tuple[str, str, str]:
    """Calculate (next_tag, major_tag, minor_tag)."""
    if not current_tag:
        major, minor, patch = (1, 0, 0)
    else:
        parsed = parse_semver(current_tag)
        if not parsed:
            major, minor, patch = (1, 0, 0)
        else:
            major, minor, patch = parsed
            if bump_type == "major":
                major += 1
                minor = 0
                patch = 0
            elif bump_type == "minor":
                minor += 1
                patch = 0
            elif bump_type == "patch":
                patch += 1

    next_tag = f"v{major}.{minor}.{patch}"
    major_tag = f"v{major}"
    minor_tag = f"v{major}.{minor}"
    return next_tag, major_tag, minor_tag


def main() -> None:
    force_bump = os.environ.get("INPUT_FORCE_BUMP", "auto").lower()

    latest_tag = get_latest_semver_tag()
    commits = get_commits_since_tag(latest_tag)

    if force_bump in ("major", "minor", "patch"):
        bump_type = force_bump
    else:
        bump_type = determine_bump_type(commits)

    has_changes = len(commits) > 0 or latest_tag is None
    next_tag, major_tag, minor_tag = calculate_next_version(latest_tag, bump_type if has_changes else "none")

    print(f"Latest Tag: {latest_tag or 'None (initial)'}")
    print(f"Commits since tag: {len(commits)}")
    print(f"Determined Bump: {bump_type}")
    print(f"Next Version: {next_tag}")
    print(f"Floating Major: {major_tag}")
    print(f"Floating Minor: {minor_tag}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"next-version={next_tag}\n")
            f.write(f"major-version={major_tag}\n")
            f.write(f"minor-version={minor_tag}\n")
            f.write(f"bump-type={bump_type}\n")
            f.write(f"previous-version={latest_tag or ''}\n")
            f.write(f"has-changes={'true' if has_changes else 'false'}\n")


if __name__ == "__main__":
    main()
