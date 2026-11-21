#!/usr/bin/env bash
# ==============================================================================
# Install npm dependencies across configured Node.js workspaces.
# ==============================================================================
set -euo pipefail

TARGETS="${WORKSPACES:-.}"

for ws in $TARGETS; do
	manifest="${ws%/}/package.json"
	if [ ! -f "$manifest" ]; then
		echo "::error ::package.json not found at '${manifest}'." >&2
		exit 1
	fi
	echo "==> Installing Node dependencies in ${ws}..."
	if [ -f "${ws%/}/package-lock.json" ]; then
		(cd "$ws" && npm ci)
	else
		(cd "$ws" && npm install)
	fi
done
