#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=../common/yaml-common.sh
source "${SCRIPT_DIR}/../common/yaml-common.sh"

export SOPS_AGE_KEY="${AGE_KEY:-}"
TARGET_FILE="${FILE_PATH:-config/secrets.enc.yaml}"
DEST_PATH="${OUTPUT_PATH:-}"
MODE="${FILE_MODE:-0600}"
DESIRED_SOPS_VERSION="${SOPS_VERSION:-3.9.4}"

# Check prerequisites
if [ -z "$SOPS_AGE_KEY" ]; then
	echo "::notice ::No SOPS_AGE_KEY provided. Skipping decryption."
	if [ -n "${GITHUB_OUTPUT:-}" ]; then
		echo "decrypted=false" >>"$GITHUB_OUTPUT"
		echo "json={}" >>"$GITHUB_OUTPUT"
	fi
	exit 0
fi

if [ ! -f "$TARGET_FILE" ]; then
	echo "::warning ::Encrypted file '$TARGET_FILE' does not exist. Skipping decryption."
	if [ -n "${GITHUB_OUTPUT:-}" ]; then
		echo "decrypted=false" >>"$GITHUB_OUTPUT"
		echo "json={}" >>"$GITHUB_OUTPUT"
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
	CHECKSUMS_URL="https://github.com/getsops/sops/releases/download/v${DESIRED_SOPS_VERSION}/sops-v${DESIRED_SOPS_VERSION}.checksums.txt"
	INSTALL_DIR="${RUNNER_TEMP:-/tmp}/bin"
	mkdir -p "$INSTALL_DIR"
	curl -fsSL "$DOWNLOAD_URL" -o "${INSTALL_DIR}/sops"
	curl -fsSL "$CHECKSUMS_URL" -o "${INSTALL_DIR}/sops.checksums.txt"

	(
		cd "$INSTALL_DIR"
		EXPECTED_HASH="$(grep "sops-v${DESIRED_SOPS_VERSION}.linux.${ARCH}$" sops.checksums.txt | awk '{print $1}')"
		if [ -z "$EXPECTED_HASH" ]; then
			echo "::error ::Could not find checksum for sops-v${DESIRED_SOPS_VERSION}.linux.${ARCH} in sops.checksums.txt"
			exit 1
		fi
		echo "${EXPECTED_HASH}  sops" | sha256sum -c -
		rm -f sops.checksums.txt
	)

	chmod +x "${INSTALL_DIR}/sops"
	export PATH="${INSTALL_DIR}:${PATH}"
	if [ -n "${GITHUB_PATH:-}" ]; then
		echo "$INSTALL_DIR" >>"$GITHUB_PATH"
	fi
fi

# Decrypt plaintext file only if DEST_PATH is explicitly set
if [ -n "$DEST_PATH" ]; then
	mkdir -p "$(dirname "$DEST_PATH")"
	echo "Decrypting '$TARGET_FILE' -> '$DEST_PATH'..."
	sops --decrypt "$TARGET_FILE" >"$DEST_PATH"
	chmod "$MODE" "$DEST_PATH"
	echo "::notice ::Successfully decrypted '$TARGET_FILE' to '$DEST_PATH' (mode: $MODE)."
else
	echo "::notice ::Decrypted keys extracted directly to memory without disk persistence."
fi

if [ -n "${GITHUB_OUTPUT:-}" ]; then
	echo "decrypted=true" >>"$GITHUB_OUTPUT"
fi

# Extract requested keys into a masked JSON object using native sops JSON output
if [ -n "${KEYS:-}" ]; then
	if [ -n "$DEST_PATH" ] && command -v yq >/dev/null 2>&1; then
		json_raw="$(yq -o=json '.' "$DEST_PATH")"
	else
		json_raw="$(sops --decrypt --output-type json "$TARGET_FILE")"
	fi
	json_out="$(filter_json_keys "$json_raw" "${KEYS:-}" "true")"
else
	json_out="{}"
fi

if [ -n "${GITHUB_OUTPUT:-}" ]; then
	echo "json=$json_out" >>"$GITHUB_OUTPUT"
fi
