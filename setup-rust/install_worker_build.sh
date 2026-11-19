#!/usr/bin/env bash
# ==============================================================================
# Install worker-build for Cloudflare Rust Workers if not already in PATH.
# ==============================================================================
set -euo pipefail

if command -v worker-build >/dev/null 2>&1; then
	echo "worker-build is already available in PATH."
	exit 0
fi

VERSION_ARGS=()
if [ -n "${WORKER_BUILD_VERSION:-}" ]; then
	VERSION_ARGS=(--version "$WORKER_BUILD_VERSION")
fi

echo "Installing worker-build${WORKER_BUILD_VERSION:+ v${WORKER_BUILD_VERSION}}..."
if command -v cargo-binstall >/dev/null 2>&1; then
	cargo binstall --no-confirm --locked worker-build ${VERSION_ARGS[@]+"${VERSION_ARGS[@]}"}
else
	cargo install -q --locked worker-build ${VERSION_ARGS[@]+"${VERSION_ARGS[@]}"}
fi
