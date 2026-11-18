#!/usr/bin/env bash
# ==============================================================================
# Clone hook repositories at pinned revs and discover required mise tools
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${HOME}/.local/share/pre-commit-venv"
export PATH="${VENV_DIR}/bin:${HOME}/.local/bin:${PATH}"

WORKSPACE="${GITHUB_WORKSPACE:-.}"
cd "$WORKSPACE"

if [ -f ".pre-commit-config.yaml" ]; then
    git config --global --add safe.directory "*"
    pre-commit install-hooks
fi

"${VENV_DIR}/bin/python" "${SCRIPT_DIR}/discover_tools.py"
