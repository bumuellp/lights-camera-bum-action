#!/usr/bin/env bash
# ==============================================================================
# Install Playwright browsers or OS dependencies across configured workspaces.
# ==============================================================================
set -euo pipefail

TARGETS="${WORKSPACES:-.}"
BROWSERS_ARR=()
if [ -n "${PLAYWRIGHT_BROWSERS:-chromium}" ]; then
	read -r -a BROWSERS_ARR <<<"${PLAYWRIGHT_BROWSERS:-chromium}"
fi

for ws in $TARGETS; do
	manifest="${ws%/}/package.json"
	if [ ! -f "$manifest" ]; then
		echo "::error ::package.json not found at '${manifest}'." >&2
		exit 1
	fi
	if [ "${PLAYWRIGHT_CACHE_HIT:-false}" = "true" ]; then
		echo "==> Installing Playwright OS dependencies in ${ws}..."
		(cd "$ws" && npx playwright install-deps ${BROWSERS_ARR[@]+"${BROWSERS_ARR[@]}"})
	else
		echo "==> Installing Playwright browsers in ${ws}..."
		(cd "$ws" && npx playwright install --with-deps ${BROWSERS_ARR[@]+"${BROWSERS_ARR[@]}"})
	fi
done
