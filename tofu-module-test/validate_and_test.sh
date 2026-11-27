#!/usr/bin/env bash
# ==============================================================================
# Validate and test OpenTofu modules matching MODULES_GLOB
# ==============================================================================
set -euo pipefail
shopt -s nullglob

MODULES_GLOB="${MODULES_GLOB:-modules/*}"
RUN_TESTS="${RUN_TESTS:-true}"
CACHE_PROVIDERS="${CACHE_PROVIDERS:-true}"
TF_PLUGIN_CACHE_DIR="${TF_PLUGIN_CACHE_DIR:-${RUNNER_TEMP:-/tmp}/tofu-plugin-cache}"

if [ "$CACHE_PROVIDERS" = "true" ]; then
	mkdir -p "$TF_PLUGIN_CACHE_DIR"
	export TF_PLUGIN_CACHE_DIR
else
	unset TF_PLUGIN_CACHE_DIR
fi

read -r -a patterns <<<"$MODULES_GLOB"
validated=0

for pattern in "${patterns[@]}"; do
	# shellcheck disable=SC2206
	matches=($pattern)
	for mod in "${matches[@]}"; do
		[ -d "$mod" ] || continue
		echo "=== Validating $mod ==="
		tofu -chdir="$mod" init -backend=false -input=false
		tofu -chdir="$mod" validate
		validated=$((validated + 1))

		if [ "$RUN_TESTS" = "true" ]; then
			test_files=(
				"$mod"/*.tftest.hcl
				"$mod"/*.tftest.json
				"$mod"/tests/*.tftest.hcl
				"$mod"/tests/*.tftest.json
			)
			if [ "${#test_files[@]}" -gt 0 ]; then
				echo "=== Running OpenTofu tests in $mod ==="
				tofu -chdir="$mod" test
			fi
		fi
	done
done

if [ "$validated" -eq 0 ]; then
	echo "ERROR: No OpenTofu modules found matching: $MODULES_GLOB" >&2
	exit 1
fi
