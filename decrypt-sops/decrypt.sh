#!/usr/bin/env bash
set -euo pipefail

# Decrypt helper for SOPS using an Age secret key
# Environment variables:
#   AGE_KEY: Age private key (SOPS_AGE_KEY)
#   FILE_PATH: Path to the encrypted file
#   OUTPUT_PATH: Destination path for the decrypted file
#   FILE_MODE: File permissions mode (e.g. 0600)
#   SOPS_VERSION: SOPS binary release version to download if missing

export SOPS_AGE_KEY="${AGE_KEY:-}"
TARGET_FILE="${FILE_PATH:-config/secrets.enc.yaml}"
DEST_PATH="${OUTPUT_PATH:-config/secrets.yaml}"
MODE="${FILE_MODE:-0600}"
DESIRED_SOPS_VERSION="${SOPS_VERSION:-3.9.4}"

# Check prerequisites
if [ -z "$SOPS_AGE_KEY" ]; then
	echo "::notice ::No SOPS_AGE_KEY provided. Skipping decryption."
	if [ -n "${GITHUB_OUTPUT:-}" ]; then
		echo "decrypted=false" >>"$GITHUB_OUTPUT"
	fi
	exit 0
fi

if [ ! -f "$TARGET_FILE" ]; then
	echo "::warning ::Encrypted file '$TARGET_FILE' does not exist. Skipping decryption."
	if [ -n "${GITHUB_OUTPUT:-}" ]; then
		echo "decrypted=false" >>"$GITHUB_OUTPUT"
	fi
	exit 0
fi

# Ensure sops is installed
if ! command -v sops >/dev/null 2>&1; then
	echo "::info ::sops not found in PATH. Downloading sops v${DESIRED_SOPS_VERSION}..."
	RUNNER_ARCH="$(uname -m)"
	case "$RUNNER_ARCH" in
	x86_64) ARCH="amd64" ;;
	aarch64 | arm64) ARCH="arm64" ;;
	*)
		echo "::error ::Unsupported runner architecture: $RUNNER_ARCH"
		exit 1
		;;
	esac

	DOWNLOAD_URL="https://github.com/getsops/sops/releases/download/v${DESIRED_SOPS_VERSION}/sops-v${DESIRED_SOPS_VERSION}.linux.${ARCH}"
	INSTALL_DIR="${RUNNER_TEMP:-/tmp}/bin"
	mkdir -p "$INSTALL_DIR"
	curl -fsSL "$DOWNLOAD_URL" -o "${INSTALL_DIR}/sops"
	chmod +x "${INSTALL_DIR}/sops"
	export PATH="${INSTALL_DIR}:${PATH}"
	if [ -n "${GITHUB_PATH:-}" ]; then
		echo "$INSTALL_DIR" >>"$GITHUB_PATH"
	fi
fi

# Create target directory if needed
mkdir -p "$(dirname "$DEST_PATH")"

echo "Decrypting '$TARGET_FILE' -> '$DEST_PATH'..."
sops --decrypt "$TARGET_FILE" >"$DEST_PATH"
chmod "$MODE" "$DEST_PATH"

echo "::notice ::Successfully decrypted '$TARGET_FILE' to '$DEST_PATH' (mode: $MODE)."
if [ -n "${GITHUB_OUTPUT:-}" ]; then
	echo "decrypted=true" >>"$GITHUB_OUTPUT"
fi
