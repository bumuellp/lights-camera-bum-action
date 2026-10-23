#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=../common/yaml-common.sh
source "${SCRIPT_DIR}/../common/yaml-common.sh"

TARGET_FILE="${CONFIG_FILE:-config/settings.yaml}"
FALLBACK="${FALLBACK_FILE:-config/settings.example.yaml}"
MASK="${MASK_VALUES:-false}"
DESIRED_YQ_VERSION="${YQ_VERSION:-v4.44.6}"

FILE_TO_READ=""
if [ -f "$TARGET_FILE" ]; then
	FILE_TO_READ="$TARGET_FILE"
elif [ -n "$FALLBACK" ] && [ -f "$FALLBACK" ]; then
	FILE_TO_READ="$FALLBACK"
else
	echo "::warning ::Neither '$TARGET_FILE' nor fallback '$FALLBACK' exists."
	if [ -n "${GITHUB_OUTPUT:-}" ]; then
		echo "json={}" >>"$GITHUB_OUTPUT"
	fi
	exit 0
fi

echo "Parsing configuration from '$FILE_TO_READ'..."

# Ensure yq is installed
if ! command -v yq >/dev/null 2>&1; then
	echo "::info ::yq not found in PATH. Downloading yq ${DESIRED_YQ_VERSION}..."
	RUNNER_ARCH="$(uname -m)"
	case "$RUNNER_ARCH" in
	x86_64) ARCH="amd64" ;;
	aarch64 | arm64) ARCH="arm64" ;;
	*)
		echo "::error ::Unsupported runner architecture: $RUNNER_ARCH"
		exit 1
		;;
	esac

	DOWNLOAD_URL="https://github.com/mikefarah/yq/releases/download/${DESIRED_YQ_VERSION}/yq_linux_${ARCH}"
	CHECKSUMS_URL="https://github.com/mikefarah/yq/releases/download/${DESIRED_YQ_VERSION}/checksums"
	INSTALL_DIR="${RUNNER_TEMP:-/tmp}/bin"
	mkdir -p "$INSTALL_DIR"
	curl -fsSL "$DOWNLOAD_URL" -o "${INSTALL_DIR}/yq"
	curl -fsSL "$CHECKSUMS_URL" -o "${INSTALL_DIR}/yq.checksums"

	(
		cd "$INSTALL_DIR"
		EXPECTED_HASH="$(grep -E "^yq_linux_${ARCH}[[:space:]]" yq.checksums | awk '{print $19}')"
		if [ -z "$EXPECTED_HASH" ]; then
			echo "::error ::Could not find SHA-256 checksum for yq_linux_${ARCH} in yq.checksums"
			exit 1
		fi
		echo "${EXPECTED_HASH}  yq" | sha256sum -c -
		rm -f yq.checksums
	)

	chmod +x "${INSTALL_DIR}/yq"
	export PATH="${INSTALL_DIR}:${PATH}"
	if [ -n "${GITHUB_PATH:-}" ]; then
		echo "$INSTALL_DIR" >>"$GITHUB_PATH"
	fi
fi

json_raw="$(yq -o=json '.' "$FILE_TO_READ")"
json_out="$(filter_json_keys "$json_raw" "${KEYS:-}" "$MASK")"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
	echo "json=$json_out" >>"$GITHUB_OUTPUT"
fi
