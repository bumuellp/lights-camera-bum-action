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

NAME_ARGS=()
if [ -n "${WORKER_NAME:-}" ]; then
	NAME_ARGS+=(--name "$WORKER_NAME")
fi

VAR_ARGS=()
if [ -n "${WORKER_VARS:-}" ]; then
	while IFS= read -r var_name; do
		[ -z "$var_name" ] && continue

		if [ -z "${!var_name+x}" ]; then
			echo "::warning ::Runtime var '$var_name' requested but not set in step environment. Skipping."
			continue
		fi

		var_val="${!var_name}"
		if [ -n "$var_val" ]; then
			VAR_ARGS+=(--var "${var_name}:${var_val}")
		fi
	done < <(printf '%s\n' "$WORKER_VARS" | tr ', \t' '\n' | tr -d '\r' | grep -v '^$' || true)
fi

echo "Deploying worker via Wrangler..."
npx --yes wrangler deploy ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} ${NAME_ARGS[@]+"${NAME_ARGS[@]}"} ${VAR_ARGS[@]+"${VAR_ARGS[@]}"}

# Provision any requested secrets after worker exists in one bulk request
if [ -n "${WORKER_SECRETS:-}" ]; then
	SECRET_NAMES=()
	while IFS= read -r sec_name; do
		[ -z "$sec_name" ] && continue

		sec_val="${!sec_name:-}"
		if [ -n "$sec_val" ]; then
			echo "::add-mask::$sec_val"
			SECRET_NAMES+=("$sec_name")
		else
			echo "::warning ::Secret '$sec_name' requested but not set in step environment. Skipping."
		fi
	done < <(printf '%s\n' "$WORKER_SECRETS" | tr ', \t' '\n' | tr -d '\r' | grep -v '^$' || true)

	if [ "${#SECRET_NAMES[@]}" -gt 0 ]; then
		echo "Provisioning ${#SECRET_NAMES[@]} secret(s) in bulk..."
		if command -v python3 >/dev/null 2>&1; then
			BULK_JSON="$(python3 -c '
import json, os, sys
out = {n: os.environ[n] for n in sys.argv[1:] if os.environ.get(n, "")}
sys.stdout.write(json.dumps(out))
			' "${SECRET_NAMES[@]}")"
		else
			BULK_JSON="$(node -e '
				const out = {};
				for (const name of process.argv.slice(1)) {
					const val = process.env[name] ?? "";
					if (val !== "") out[name] = val;
				}
				process.stdout.write(JSON.stringify(out));
			' "${SECRET_NAMES[@]}")"
		fi
		printf '%s' "$BULK_JSON" | npx --yes wrangler secret bulk ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} ${NAME_ARGS[@]+"${NAME_ARGS[@]}"}
	fi
fi

echo "::notice ::Cloudflare Worker successfully deployed!"
