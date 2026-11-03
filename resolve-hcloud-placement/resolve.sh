#!/usr/bin/env bash
# ==============================================================================
# Resolve Hetzner Cloud Placement
# Evaluates Hetzner Cloud server types and locations in waterfall priority order
# to find the optimal available placement.
# ==============================================================================
set -euo pipefail

if [ -z "${HCLOUD_TOKEN:-}" ]; then
	echo "::error ::Hetzner Cloud API token (token) must be provided." >&2
	exit 1
fi

echo "::add-mask::${HCLOUD_TOKEN}"

if [ -z "${SERVER_TYPES:-}" ]; then
	echo "::error ::Candidate server types (server-types) must be provided." >&2
	exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
	echo "::error ::'curl' is required but not installed." >&2
	exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
	echo "::error ::'jq' is required but not installed." >&2
	exit 1
fi

parse_list_to_json() {
	local raw="$1"
	echo "$raw" | awk '
		{
			gsub(/[\[\]",]/, " ")
			for (i=1; i<=NF; i++) {
				val=$i
				gsub(/^[ \t\r\n]+|[ \t\r\n]+$/, "", val)
				if (length(val) > 0 && !seen[val]++) {
					items[count++] = val
				}
			}
		}
		END {
			printf "["
			for (i=0; i<count; i++) {
				printf "\"%s\"", items[i]
				if (i < count - 1) printf ", "
			}
			printf "]\n"
		}
	'
}

TYPES_JSON="$(parse_list_to_json "$SERVER_TYPES")"
if [ "$TYPES_JSON" = "[]" ]; then
	echo "::error ::Candidate server types list is empty." >&2
	exit 1
fi

LOCS_RAW="${LOCATIONS:-fsn1}"
LOCS_JSON="$(parse_list_to_json "$LOCS_RAW")"
if [ "$LOCS_JSON" = "[]" ]; then
	LOCS_JSON='["fsn1"]'
fi

STRATEGY="${STRATEGY:-type-first}"
FAIL_ON_UNAVAILABLE="${FAIL_ON_UNAVAILABLE:-true}"

echo "Fetching Hetzner Cloud server types..."
HTTP_RESP="$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer ${HCLOUD_TOKEN}" \
	"https://api.hetzner.cloud/v1/server_types?per_page=100")"
HTTP_BODY="$(echo "$HTTP_RESP" | sed '$d')"
HTTP_CODE="$(echo "$HTTP_RESP" | tail -n 1)"

if [ "$HTTP_CODE" -ne 200 ]; then
	echo "::error ::Hetzner Cloud API returned HTTP ${HTTP_CODE} when querying server types." >&2
	echo "$HTTP_BODY" >&2
	exit 1
fi

echo "Evaluating candidate placement (strategy: ${STRATEGY})..."
echo "  Server types: $(echo "$TYPES_JSON" | jq -r 'join(", ")')"
echo "  Locations:    $(echo "$LOCS_JSON" | jq -r 'join(", ")')"

MATCH_JSON="$(echo "$HTTP_BODY" | jq -r \
	--argjson types "$TYPES_JSON" \
	--argjson locs "$LOCS_JSON" \
	--arg strategy "$STRATEGY" '
	.server_types as $all |
	(first(
		(if $strategy == "location-first" then
			$locs[] as $l | $types[] as $t | {t: $t, l: $l}
		else
			$types[] as $t | $locs[] as $l | {t: $t, l: $l}
		end) as $pair |
		($all[] | select(.name == $pair.t)) as $st |
		select([$st.locations[]? | select(.name == $pair.l and .available == true)] | length > 0) |
		{
			server_type: $pair.t,
			location: $pair.l,
			architecture: $st.architecture,
			cores: $st.cores,
			memory: $st.memory
		}
	) // empty)
')"

if [ -n "$MATCH_JSON" ] && [ "$MATCH_JSON" != "null" ]; then
	CHOSEN_TYPE="$(echo "$MATCH_JSON" | jq -r '.server_type')"
	CHOSEN_LOC="$(echo "$MATCH_JSON" | jq -r '.location')"
	CHOSEN_ARCH="$(echo "$MATCH_JSON" | jq -r '.architecture')"
	CHOSEN_CORES="$(echo "$MATCH_JSON" | jq -r '.cores')"
	CHOSEN_MEMORY="$(echo "$MATCH_JSON" | jq -r '.memory')"

	echo "::notice ::Resolved available placement: model='${CHOSEN_TYPE}' (${CHOSEN_ARCH}, ${CHOSEN_CORES} vCPU, ${CHOSEN_MEMORY}GB RAM) in location='${CHOSEN_LOC}'."

	if [ -n "${GITHUB_OUTPUT:-}" ]; then
		{
			echo "server-type=${CHOSEN_TYPE}"
			echo "location=${CHOSEN_LOC}"
			echo "architecture=${CHOSEN_ARCH}"
			echo "cores=${CHOSEN_CORES}"
			echo "memory=${CHOSEN_MEMORY}"
			echo "available=true"
		} >>"$GITHUB_OUTPUT"
	fi
	exit 0
else
	FIRST_TYPE="$(echo "$TYPES_JSON" | jq -r '.[0]')"
	FIRST_LOC="$(echo "$LOCS_JSON" | jq -r '.[0]')"

	if [ "$FAIL_ON_UNAVAILABLE" = "true" ]; then
		echo "::error ::No available server placement found for types $(echo "$TYPES_JSON" | jq -r 'join(", ")') across locations $(echo "$LOCS_JSON" | jq -r 'join(", ")')." >&2
		exit 1
	else
		echo "::warning ::No available server placement found. Defaulting to '${FIRST_TYPE}' in '${FIRST_LOC}' with available=false."
		if [ -n "${GITHUB_OUTPUT:-}" ]; then
			{
				echo "server-type=${FIRST_TYPE}"
				echo "location=${FIRST_LOC}"
				echo "architecture="
				echo "cores="
				echo "memory="
				echo "available=false"
			} >>"$GITHUB_OUTPUT"
		fi
		exit 0
	fi
fi
