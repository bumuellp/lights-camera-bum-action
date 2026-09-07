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


def test_should_build_image_workflow_dispatch():
    image = {"name": "app", "path": "images/app", "dockerfile": "images/app/Dockerfile"}
    assert should_build_image(image, "workflow_dispatch", "all", []) is True
    assert should_build_image(image, "workflow_dispatch", "app", []) is True
    assert should_build_image(image, "workflow_dispatch", "other", []) is False


def test_should_build_image_push_events():
    image = {"name": "app", "path": "images/app", "dockerfile": "images/app/Dockerfile"}
    assert should_build_image(image, "push", "all", ["images/app/src/main.py"]) is True
    assert should_build_image(image, "push", "all", ["images/app/Dockerfile"]) is True
    assert should_build_image(image, "push", "all", ["images/other/file.txt"]) is False


def test_plan_builds_full_pipeline():
    raw_images = json.dumps([
        {"name": "app1", "path": "images/app1"},
        {"name": "app2", "path": "images/app2"},
    ])
    matrix, should_build = plan_builds(
        raw_images=raw_images,
        target="app1",
        event_name="workflow_dispatch",
        before_sha="",
        head_sha="",
    )
    assert should_build is True
    assert len(matrix["include"]) == 1
    assert matrix["include"][0]["image-name"] == "app1"
