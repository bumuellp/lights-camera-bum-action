#!/usr/bin/env bash
# ==============================================================================
# Setup Bats Testing Framework (bats-core)
# Downloads, installs into ~/.local, and adds ~/.local/bin to GITHUB_PATH.
# ==============================================================================
set -euo pipefail

BATS_VERSION="${BATS_VERSION:-v1.13.0}"
INSTALL_PREFIX="${HOME}/.local"
BIN_DIR="${INSTALL_PREFIX}/bin"
mkdir -p "$BIN_DIR"

if [ -x "${BIN_DIR}/bats" ]; then
	echo "bats CLI is already installed at ${BIN_DIR}/bats."
elif command -v bats >/dev/null 2>&1; then
	echo "bats CLI is already available in PATH ($(command -v bats))."
else
	echo "Downloading bats-core ${BATS_VERSION}..."
	TMP_DIR="$(mktemp -d)"
	trap 'rm -rf "$TMP_DIR"' EXIT

	DL_URL="https://github.com/bats-core/bats-core/archive/refs/tags/${BATS_VERSION}.tar.gz"
	curl -fsSL "$DL_URL" | tar -xz -C "$TMP_DIR" --strip-components=1
	"$TMP_DIR/install.sh" "$INSTALL_PREFIX"
	chmod +x "${BIN_DIR}/bats"
	echo "bats-core ${BATS_VERSION} installed successfully."
fi

if [ -n "${GITHUB_PATH:-}" ]; then
	echo "$BIN_DIR" >>"$GITHUB_PATH"
fi
