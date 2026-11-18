#!/usr/bin/env bash
# ==============================================================================
# Fallback container execution for pre-commit using ghcr.io/bumuellp/lint-tools
# ==============================================================================
set -euo pipefail

WORKSPACE="${GITHUB_WORKSPACE:-.}"
IMAGE="${CONTAINER_IMAGE:-ghcr.io/bumuellp/lint-tools:v1.4.1@sha256:3a6e02e1f03750890b4cc984e516c9552f71049829c751616b3ccb9791b02a46}"

docker run --rm \
    -v "${WORKSPACE}:/workspace" \
    -w /workspace \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e PRE_COMMIT_HOME=/tmp/pre-commit \
    "$IMAGE" \
    sh -c 'git config --global --add safe.directory "*" && pre-commit run --show-diff-on-failure '"${EXTRA_ARGS:-}"
