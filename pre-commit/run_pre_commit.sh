#!/usr/bin/env bash
# ==============================================================================
# Run pre-commit hooks natively with cached environments & mise tools on PATH
# ==============================================================================
set -euo pipefail

VENV_DIR="${HOME}/.local/share/pre-commit-venv"
MISE_SHIMS="${HOME}/.local/share/mise/shims"
export PATH="${VENV_DIR}/bin:${MISE_SHIMS}:${HOME}/.local/bin:${PATH}"

if command -v mise >/dev/null 2>&1; then
	MISE_PATHS="$(mise bin-paths 2>/dev/null | paste -sd: - || true)"
	if [ -n "$MISE_PATHS" ]; then
		export PATH="${MISE_PATHS}:${PATH}"
	fi
fi

git config --global --add safe.directory "*"

WORKSPACE="${GITHUB_WORKSPACE:-.}"
cd "$WORKSPACE"

ARGS=()
if [ -n "${EXTRA_ARGS:-}" ]; then
	read -r -a ARGS <<<"$EXTRA_ARGS"
fi

pre-commit run --show-diff-on-failure ${ARGS[@]+"${ARGS[@]}"}
