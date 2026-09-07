#!/usr/bin/env python3
"""Plan container image builds based on git changes or dispatch target."""

import json
import os
import subprocess
import sys


def parse_image_definitions(raw_images: str) -> list:
    """Parse declarative JSON image list or auto-discover from filesystem."""
    raw_images = raw_images.strip()
    if raw_images and raw_images != "auto":
        parsed = json.loads(raw_images)
        images = []
        for item in parsed:
            if isinstance(item, str):
                images.append({
                    "name": item,
                    "path": f"images/{item}",
                    "dockerfile": f"images/{item}/Dockerfile",
                })
            elif isinstance(item, dict):
                path = item.get("path", "").rstrip("/")
                name = item.get("name") or os.path.basename(path)
                dockerfile = item.get("dockerfile") or (f"{path}/Dockerfile" if path else "Dockerfile")
                images.append({
                    "name": name,
                    "path": path,
                    "dockerfile": dockerfile,
                })
        return images

    # Auto-discovery mode
    discovered = []
    if os.path.isdir("images"):
        for entry in sorted(os.listdir("images")):
            dockerfile_path = os.path.join("images", entry, "Dockerfile")
            if os.path.isfile(dockerfile_path):
                discovered.append({
                    "name": entry,
                    "path": os.path.join("images", entry),
                    "dockerfile": dockerfile_path,
                })
    return discovered


def get_changed_files(event_name: str, before_sha: str, head_sha: str) -> list:
    """Get list of changed files for push events."""
    if event_name != "push":
        return []

    if before_sha and not before_sha.startswith("0000000"):
        diff_cmd = ["git", "diff", "--name-only", before_sha, head_sha or "HEAD"]
    else:
        diff_cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]

    try:
        res = subprocess.run(diff_cmd, capture_output=True, text=True, check=False)
        if res.returncode == 0:
            return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        pass
    return []


def should_build_image(
    image: dict,
    event_name: str,
    target: str,
    changed_files: list,
) -> bool:
    """Determine if a given image should be built."""
    name = image["name"]
    path = image["path"]
    dockerfile = image["dockerfile"]

    if event_name == "workflow_dispatch":
        return target in ("all", "", name)

    # For push events:
    if not changed_files:
        # If diff couldn't be obtained or initial commit, build to be safe
        return True

    for changed in changed_files:
        if path and (changed == path or changed.startswith(f"{path}/")):
            return True
        if dockerfile and changed == dockerfile:
            return True
    return False


def plan_builds(
    raw_images: str,
    target: str,
    event_name: str,
    before_sha: str,
    head_sha: str,
) -> tuple[dict, bool]:
    """Generate the GitHub Actions matrix and should-build flag."""
    images = parse_image_definitions(raw_images)
    changed_files = get_changed_files(event_name, before_sha, head_sha)

    include = []
    for img in images:
        if should_build_image(img, event_name, target, changed_files):
            include.append({
                "image-name": img["name"],
                "context": img["path"] or ".",
                "dockerfile": img["dockerfile"],
            })

    matrix = {"include": include}
    should_build = len(include) > 0
    return matrix, should_build


def main() -> None:
    raw_images = os.environ.get("INPUT_IMAGES", "auto")
    target = os.environ.get("INPUT_TARGET", "all")
    event_name = os.environ.get("GITHUB_EVENT_NAME", "push")
    before_sha = os.environ.get("GITHUB_EVENT_BEFORE", "")
    head_sha = os.environ.get("GITHUB_SHA", "")

    matrix, should_build = plan_builds(
        raw_images=raw_images,
        target=target,
        event_name=event_name,
        before_sha=before_sha,
        head_sha=head_sha,
    )

    matrix_json = json.dumps(matrix)
    should_build_str = "true" if should_build else "false"

    print(f"Matrix: {matrix_json}")
    print(f"Should build: {should_build_str}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"matrix={matrix_json}\n")
            f.write(f"should-build={should_build_str}\n")


if __name__ == "__main__":
    main()
