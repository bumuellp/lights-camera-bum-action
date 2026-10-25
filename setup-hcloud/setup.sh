#!/usr/bin/env bash
# ==============================================================================
# Setup Hetzner Cloud CLI (hcloud)
# Downloads, verifies, and adds hcloud CLI to PATH.
# ==============================================================================
set -euo pipefail

HCLOUD_VERSION="${HCLOUD_VERSION:-v1.70.2}"
BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

if [ -n "${HCLOUD_TOKEN:-}" ]; then
	echo "::add-mask::${HCLOUD_TOKEN}"
	if [ -n "${GITHUB_ENV:-}" ]; then
		echo "HCLOUD_TOKEN=${HCLOUD_TOKEN}" >>"$GITHUB_ENV"
	fi
fi

if [ -f "${BIN_DIR}/hcloud" ] && [ -x "${BIN_DIR}/hcloud" ]; then
	echo "hcloud CLI is already installed at ${BIN_DIR}/hcloud."
elif command -v hcloud >/dev/null 2>&1; then
	echo "hcloud CLI is already available in PATH ($(command -v hcloud))."
else
	echo "Downloading hcloud CLI ${HCLOUD_VERSION}..."
	ARCH="$(uname -m)"
	case "$ARCH" in
	x86_64) ARCH_TAG="amd64" ;;
	aarch64 | arm64) ARCH_TAG="arm64" ;;
	*)
		echo "::error ::Unsupported architecture: ${ARCH}" >&2
		exit 1
		;;
	esac

	DL_URL="https://github.com/hetznercloud/cli/releases/download/${HCLOUD_VERSION}/hcloud-linux-${ARCH_TAG}.tar.gz"
	curl -fsSL "$DL_URL" | tar -xz -C "$BIN_DIR" hcloud
	chmod +x "${BIN_DIR}/hcloud"
	echo "hcloud CLI ${HCLOUD_VERSION} installed successfully."
fi

if [ -n "${GITHUB_PATH:-}" ]; then
	echo "$BIN_DIR" >>"$GITHUB_PATH"
fi
