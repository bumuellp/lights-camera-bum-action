#!/usr/bin/env bash
# ==============================================================================
# Ensure isolated pre-commit Python environment exists
# ==============================================================================
set -euo pipefail

VENV_DIR="${HOME}/.local/share/pre-commit-venv"
VERSION="${PRE_COMMIT_VERSION:-4.6.2}"
MARKER_FILE="${VENV_DIR}/.installed-version"

if [ -x "${VENV_DIR}/bin/pre-commit" ] && [ -f "$MARKER_FILE" ] && [ "$(cat "$MARKER_FILE")" = "$VERSION" ]; then
    echo "pre-commit v${VERSION} is already installed."
    exit 0
fi

echo "Installing pre-commit==${VERSION} into ${VENV_DIR}..."
python3 -m venv "$VENV_DIR"
if command -v uv >/dev/null 2>&1; then
    uv pip install --python "${VENV_DIR}/bin/python" --quiet "pre-commit==${VERSION}"
else
    "${VENV_DIR}/bin/pip" install --quiet --no-cache-dir "pre-commit==${VERSION}"
fi
printf '%s' "$VERSION" >"$MARKER_FILE"
