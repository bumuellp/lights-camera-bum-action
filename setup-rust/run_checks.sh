#!/usr/bin/env bash
# ==============================================================================
# Run optional Rust quality gates (fmt, clippy, test) across configured crates.
# Environment variables:
#   WORKSPACES:  Space-separated crate/workspace paths (defaults to '.')
#   RUN_FMT:     'true' to run cargo fmt --check
#   RUN_CLIPPY:  'true' to run cargo clippy
#   CLIPPY_ARGS: Extra arguments passed to cargo clippy
#   RUN_TEST:    'true' to run cargo test
#   TEST_ARGS:   Extra arguments passed to cargo test
# ==============================================================================
set -euo pipefail

TARGETS="${WORKSPACES:-.}"

run_cargo_for_workspaces() {
	local subcommand="$1"
	shift
	local ws
	for ws in $TARGETS; do
		local manifest="${ws%/}/Cargo.toml"
		if [ ! -f "$manifest" ]; then
			echo "::error ::Cargo manifest not found at '${manifest}'." >&2
			exit 1
		fi
		echo "==> Running cargo ${subcommand} for ${manifest}..."
		cargo "$subcommand" --manifest-path "$manifest" "$@"
	done
}

if [ "${RUN_FMT:-false}" = "true" ]; then
	run_cargo_for_workspaces fmt --check
fi

if [ "${RUN_CLIPPY:-false}" = "true" ]; then
	CLIPPY_ARR=()
	if [ -n "${CLIPPY_ARGS:-}" ]; then
		read -r -a CLIPPY_ARR <<<"$CLIPPY_ARGS"
	fi
	run_cargo_for_workspaces clippy ${CLIPPY_ARR[@]+"${CLIPPY_ARR[@]}"}
fi

if [ "${RUN_TEST:-false}" = "true" ]; then
	TEST_ARR=()
	if [ -n "${TEST_ARGS:-}" ]; then
		read -r -a TEST_ARR <<<"$TEST_ARGS"
	fi
	run_cargo_for_workspaces test ${TEST_ARR[@]+"${TEST_ARR[@]}"}
fi
