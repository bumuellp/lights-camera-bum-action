#!/usr/bin/env bash
# ==============================================================================
# Install worker-build for Cloudflare Rust Workers if not already in PATH.
# ==============================================================================
set -euo pipefail

if ! command -v worker-build >/dev/null 2>&1; then
    echo "Installing worker-build..."
    cargo install -q worker-build
else
    echo "worker-build is already available in PATH."
fi
