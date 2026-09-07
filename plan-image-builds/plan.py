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


def get_changed_files(before_sha: str, head_sha: str) -> list:
    """Get list of changed files from git diff."""
    diff_cmds = []
    if before_sha and not before_sha.startswith("0000000"):
        diff_cmds.append(["git", "diff", "--name-only", before_sha, head_sha or "HEAD"])
    diff_cmds.append(["git", "diff", "--name-only", "HEAD~1", "HEAD"])
    diff_cmds.append(["git", "diff", "--name-only", "origin/main...HEAD"])
    diff_cmds.append(["git", "diff", "--name-only", "HEAD"])

    for cmd in diff_cmds:
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return [line.strip() for line in res.stdout.splitlines() if line.strip()]
        except Exception:
            pass
    return []


def should_build_image(
    image: dict,
    target: str,
    changed_files: list,
) -> bool:
    """Determine if a given image should be built."""
    name = image["name"]
    path = image["path"]
    dockerfile = image["dockerfile"]

    # Normalize targets: supports comma/space-separated values (e.g., "mcpo, openclaw", "none")
    raw_targets = {t.strip() for t in target.replace(",", " ").split() if t.strip()}
    if not raw_targets:
        raw_targets = {"auto"}

    # 1. Force all images
    if "all" in raw_targets:
        return True

    # 2. Explicit 'none' (e.g., custom mode with no checkboxes checked)
    if "none" in raw_targets:
        return False

    # 3. Explicit subset or single image (e.g. "mcpo, openclaw" or "lint-tools")
    if "auto" not in raw_targets:
        return name in raw_targets

    # 4. Auto mode: git diff path filtering
    if not changed_files:
        return False

    for changed in changed_files:
        if path and (changed == path or changed.startswith(f"{path}/")):
            return True
        if dockerfile and changed == dockerfile:
            return True
    return False


def plan_builds(
    raw_images: str,
    target: str,
    before_sha: str,
    head_sha: str,
) -> tuple[dict, bool]:
    """Generate the GitHub Actions matrix and should-build flag."""
    images = parse_image_definitions(raw_images)
    changed_files = get_changed_files(before_sha, head_sha)

    include = []
    for img in images:
        if should_build_image(img, target, changed_files):
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
    before_sha = os.environ.get("GITHUB_EVENT_BEFORE", "")
    head_sha = os.environ.get("GITHUB_SHA", "")

    matrix, should_build = plan_builds(
        raw_images=raw_images,
        target=target,
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
