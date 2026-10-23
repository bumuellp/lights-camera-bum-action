#!/usr/bin/env bash
set -euo pipefail

# Deploy Cloudflare Worker using Wrangler
# Environment variables:
#   CLOUDFLARE_API_TOKEN: API Token
#   WORKER_ENV: Optional target environment
#   WORKER_SECRETS: Multiline or space/comma-separated list of secret names to upload via wrangler secret put

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
	echo "::error ::Missing CLOUDFLARE_API_TOKEN. Deployment aborted."
	exit 1
fi
echo "::add-mask::$CLOUDFLARE_API_TOKEN"

if [ ! -f "wrangler.toml" ] && [ ! -f "wrangler.json" ] && [ ! -f "wrangler.jsonc" ]; then
	echo "::error ::No wrangler configuration found in $(pwd)."
	exit 1
fi

# If Cargo.toml exists, ensure worker-build is installed
if [ -f "Cargo.toml" ] && ! command -v worker-build >/dev/null 2>&1; then
	echo "Rust worker detected. Installing worker-build..."
	cargo install -q worker-build
fi

ENV_ARGS=()
if [ -n "${WORKER_ENV:-}" ]; then
	ENV_ARGS+=(--env "$WORKER_ENV")
fi

echo "Deploying worker via Wrangler..."
npx --yes wrangler deploy ${ENV_ARGS[@]+"${ENV_ARGS[@]}"}

# Provision any requested secrets after worker exists
if [ -n "${WORKER_SECRETS:-}" ]; then
	while IFS= read -r sec_name; do
		[ -z "$sec_name" ] && continue

		sec_val="${!sec_name:-}"
		if [ -n "$sec_val" ]; then
			echo "::add-mask::$sec_val"
			echo "Provisioning secret '$sec_name'..."
			printf '%s' "$sec_val" | npx --yes wrangler secret put "$sec_name" ${ENV_ARGS[@]+"${ENV_ARGS[@]}"}
		else
			echo "::warning ::Secret '$sec_name' requested but not set in step environment. Skipping."
		fi
	done < <(printf '%s\n' "$WORKER_SECRETS" | tr ', \t' '\n' | tr -d '\r' | grep -v '^$' || true)
fi

echo "::notice ::Cloudflare Worker successfully deployed!"
