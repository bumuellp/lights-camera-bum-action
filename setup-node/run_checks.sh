#!/usr/bin/env bash
# ==============================================================================
# Run optional Node.js quality gates (lint, typecheck, build, test).
# ==============================================================================
set -euo pipefail

TARGETS="${WORKSPACES:-.}"

run_npm_script_for_workspaces() {
	local script_name="$1"
	local ws
	for ws in $TARGETS; do
		local manifest="${ws%/}/package.json"
		if [ ! -f "$manifest" ]; then
			echo "::error ::package.json not found at '${manifest}'." >&2
			exit 1
		fi
		echo "==> Running npm run ${script_name} in ${ws}..."
		(cd "$ws" && npm run "$script_name")
	done
}

if [ "${RUN_LINT:-false}" = "true" ]; then
	run_npm_script_for_workspaces "${LINT_SCRIPT:-lint}"
fi

if [ "${RUN_TYPECHECK:-false}" = "true" ]; then
	run_npm_script_for_workspaces "${TYPECHECK_SCRIPT:-typecheck}"
fi

if [ "${RUN_BUILD:-false}" = "true" ]; then
	run_npm_script_for_workspaces "${BUILD_SCRIPT:-build}"
fi

if [ "${RUN_TEST:-false}" = "true" ]; then
	run_npm_script_for_workspaces "${TEST_SCRIPT:-test}"
fi
