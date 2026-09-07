"""Unit tests for plan.py in lights-camera-bum-action."""

import json
from pathlib import Path
import sys
import pytest

# Ensure plan-image-builds directory is importable
ACTION_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ACTION_ROOT / "plan-image-builds"))

from plan import parse_image_definitions, should_build_image, plan_builds


def test_parse_image_definitions_explicit_json():
    raw_images = json.dumps([
        {"name": "custom-name", "path": "src/app", "dockerfile": "src/app/custom.dockerfile"},
        {"path": "images/simple-svc"},
        "string-shortcut",
    ])
    images = parse_image_definitions(raw_images)
    assert len(images) == 3
    assert images[0] == {
        "name": "custom-name",
        "path": "src/app",
        "dockerfile": "src/app/custom.dockerfile",
    }
    assert images[1] == {
        "name": "simple-svc",
        "path": "images/simple-svc",
        "dockerfile": "images/simple-svc/Dockerfile",
    }
    assert images[2] == {
        "name": "string-shortcut",
        "path": "images/string-shortcut",
        "dockerfile": "images/string-shortcut/Dockerfile",
    }


def test_parse_image_definitions_auto_discovery(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    images_dir = tmp_path / "images"
    (images_dir / "service-a").mkdir(parents=True)
    (images_dir / "service-a" / "Dockerfile").write_text("FROM alpine")
    (images_dir / "service-b").mkdir(parents=True)
    (images_dir / "service-b" / "Dockerfile").write_text("FROM debian")

    images = parse_image_definitions("auto")
    assert len(images) == 2
    assert images[0]["name"] == "service-a"
    assert images[1]["name"] == "service-b"


def test_should_build_image_explicit_targets():
    image = {"name": "app", "path": "images/app", "dockerfile": "images/app/Dockerfile"}
    assert should_build_image(image, "all", []) is True
    assert should_build_image(image, "app", []) is True
    assert should_build_image(image, "other", []) is False


def test_should_build_image_multi_target_selection():
    img1 = {"name": "lint-tools", "path": "images/lint-tools", "dockerfile": "images/lint-tools/Dockerfile"}
    img2 = {"name": "mcpo", "path": "images/mcpo", "dockerfile": "images/mcpo/Dockerfile"}
    img3 = {"name": "openclaw", "path": "images/openclaw", "dockerfile": "images/openclaw/Dockerfile"}

    # Comma-separated
    target_str = "lint-tools, mcpo"
    assert should_build_image(img1, target_str, []) is True
    assert should_build_image(img2, target_str, []) is True
    assert should_build_image(img3, target_str, []) is False

    # Space-separated
    target_space = "mcpo openclaw"
    assert should_build_image(img1, target_space, []) is False
    assert should_build_image(img2, target_space, []) is True
    assert should_build_image(img3, target_space, []) is True


def test_should_build_image_none_or_empty_custom():
    image = {"name": "app", "path": "images/app", "dockerfile": "images/app/Dockerfile"}
    assert should_build_image(image, "none", []) is False
    assert should_build_image(image, "none", ["images/app/Dockerfile"]) is False


def test_should_build_image_auto_path_detection():
    image = {"name": "app", "path": "images/app", "dockerfile": "images/app/Dockerfile"}
    assert should_build_image(image, "auto", ["images/app/src/main.py"]) is True
    assert should_build_image(image, "auto", ["images/app/Dockerfile"]) is True
    assert should_build_image(image, "auto", ["images/other/file.txt"]) is False
    assert should_build_image(image, "auto", []) is False


def test_plan_builds_full_pipeline_multi_target():
    raw_images = json.dumps([
        {"name": "lint-tools", "path": "images/lint-tools"},
        {"name": "mcpo", "path": "images/mcpo"},
        {"name": "openclaw", "path": "images/openclaw"},
    ])
    matrix, should_build = plan_builds(
        raw_images=raw_images,
        target="lint-tools, openclaw",
        before_sha="",
        head_sha="",
    )
    assert should_build is True
    assert len(matrix["include"]) == 2
    names = [item["image-name"] for item in matrix["include"]]
    assert "lint-tools" in names
    assert "openclaw" in names
    assert "mcpo" not in names


def test_plan_builds_empty_selection_no_op():
    raw_images = json.dumps([
        {"name": "lint-tools", "path": "images/lint-tools"},
        {"name": "mcpo", "path": "images/mcpo"},
    ])
    matrix, should_build = plan_builds(
        raw_images=raw_images,
        target="none",
        before_sha="",
        head_sha="",
    )
    assert should_build is False
    assert len(matrix["include"]) == 0
