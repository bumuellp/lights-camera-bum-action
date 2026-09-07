#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${1:-ghcr.io}"
REPO_OWNER="${2:?Repository owner is required}"
IMAGE_NAME="${3:?Image name is required}"
SHA="${4:-}"
EXTRA_TAGS="${5:-}"

TAGS="${REGISTRY}/${REPO_OWNER}/${IMAGE_NAME}:latest"

if [ -n "$SHA" ]; then
  TAGS="${TAGS}"$'\n'"${REGISTRY}/${REPO_OWNER}/${IMAGE_NAME}:${SHA}"
fi

if [ -n "$EXTRA_TAGS" ]; then
  IFS=', ' read -r -a EXTRA_ARRAY <<< "$EXTRA_TAGS"
  for tag in "${EXTRA_ARRAY[@]}"; do
    tag="$(echo "$tag" | xargs)"
    if [ -n "$tag" ]; then
      TAGS="${TAGS}"$'\n'"${REGISTRY}/${REPO_OWNER}/${IMAGE_NAME}:${tag}"
    fi
  done
fi

echo "$TAGS"
