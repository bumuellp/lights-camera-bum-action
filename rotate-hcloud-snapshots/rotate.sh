#!/usr/bin/env bash
# ==============================================================================
# Hetzner Cloud Snapshot Rotation Script
# Prunes older snapshot images matching a label selector to maintain a target retention count.
# ==============================================================================
set -euo pipefail

if [ -z "${HCLOUD_TOKEN:-}" ]; then
	echo "::error ::Hetzner Cloud API token (token) must be provided." >&2
	exit 1
fi

if [ -z "${LABEL_SELECTOR:-}" ]; then
	echo "::error ::Label selector (label-selector) must be provided." >&2
	exit 1
fi

KEEP_COUNT="${KEEP_COUNT:-1}"
if ! [[ "$KEEP_COUNT" =~ ^[0-9]+$ ]]; then
	echo "::error ::keep must be a non-negative integer. Received: '${KEEP_COUNT}'" >&2
	exit 1
fi

if ! command -v hcloud >/dev/null 2>&1; then
	echo "::error ::'hcloud' CLI is required but not installed." >&2
	exit 1
fi

echo "Querying Hetzner Cloud snapshots with label '${LABEL_SELECTOR}' (retaining newest ${KEEP_COUNT})..."

# List matching snapshots sorted by created date descending (IDs only)
SNAPSHOT_IDS="$(hcloud image list --type snapshot --selector "$LABEL_SELECTOR" --sort created:desc -o noheader -o columns=id)"

# Count total matching snapshots
TOTAL_FOUND="$(echo "$SNAPSHOT_IDS" | grep -E -c '^[[:space:]]*[0-9]+' || true)"

if [ "$TOTAL_FOUND" -eq 0 ]; then
	echo "Found 0 snapshot(s) matching '${LABEL_SELECTOR}'. Nothing to rotate."
	exit 0
fi

echo "Found ${TOTAL_FOUND} snapshot(s) matching '${LABEL_SELECTOR}'."

if [ "$TOTAL_FOUND" -le "$KEEP_COUNT" ]; then
	echo "No old snapshots to delete. Current count (${TOTAL_FOUND}) is within retention limit (${KEEP_COUNT})."
	exit 0
fi

# Select snapshots beyond KEEP_COUNT (skip newest KEEP_COUNT entries)
DROP_START=$((KEEP_COUNT + 1))
OLD_SNAPSHOTS="$(echo "$SNAPSHOT_IDS" | tail -n "+${DROP_START}")"

echo "$OLD_SNAPSHOTS" | while read -r SNAPSHOT_ID; do
	[[ "$SNAPSHOT_ID" =~ ^[0-9]+$ ]] || continue

	echo "Deleting old snapshot: ID=${SNAPSHOT_ID}..."
	hcloud image delete "$SNAPSHOT_ID"
	echo "Successfully deleted snapshot ${SNAPSHOT_ID}."
done

echo "Snapshot rotation completed successfully. Retained newest ${KEEP_COUNT} snapshot(s)."
