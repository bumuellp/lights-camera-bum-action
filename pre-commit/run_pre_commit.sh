#!/usr/bin/env bash
# ==============================================================================
# Run pre-commit hooks natively using cached binaries & hook environments
# ==============================================================================
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
VENV_DIR="${HOME}/.local/share/pre-commit-venv"
export PATH="${VENV_DIR}/bin:${BIN_DIR}:${PATH}"

git config --global --add safe.directory "*"

WORKSPACE="${GITHUB_WORKSPACE:-.}"
cd "$WORKSPACE"

ARGS=()
if [ -n "${EXTRA_ARGS:-}" ]; then
    read -r -a ARGS <<<"$EXTRA_ARGS"
fi

pre-commit run --show-diff-on-failure ${ARGS[@]+"${ARGS[@]}"}
