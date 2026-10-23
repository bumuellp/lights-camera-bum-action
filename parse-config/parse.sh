#!/usr/bin/env bash
set -euo pipefail

TARGET_FILE="${CONFIG_FILE:-config/settings.yaml}"
FALLBACK="${FALLBACK_FILE:-config/settings.example.yaml}"
MASK="${MASK_VALUES:-false}"

FILE_TO_READ=""
if [ -f "$TARGET_FILE" ]; then
	FILE_TO_READ="$TARGET_FILE"
elif [ -n "$FALLBACK" ] && [ -f "$FALLBACK" ]; then
	FILE_TO_READ="$FALLBACK"
else
	echo "::warning ::Neither '$TARGET_FILE' nor fallback '$FALLBACK' exists."
	if [ -n "${GITHUB_OUTPUT:-}" ]; then
		echo "json={}" >>"$GITHUB_OUTPUT"
	fi
	exit 0
fi

echo "Parsing configuration from '$FILE_TO_READ'..."
json_pairs=()

while IFS= read -r key || [ -n "$key" ]; do
	key="$(echo "$key" | tr -d ' ,' | tr -d '\r')"
	[ -z "$key" ] && continue

	val="$(awk -v k="$key" '
		$1 == k ":" {
			sub(/^[^:]*:[ \t]*/, "")
			if ($0 ~ /^"/) {
				sub(/^"/, "")
				sub(/".*$/, "")
			} else if ($0 ~ /^\x27/) {
				sub(/^\x27/, "")
				sub(/\x27.*$/, "")
			} else {
				sub(/[ \t]+#.*$/, "")
				sub(/[ \t]+$/, "")
			}
			print
			exit
		}
	' "$FILE_TO_READ")"

	if [ -n "$val" ]; then
		if [ "$MASK" = "true" ]; then
			echo "::add-mask::$val"
		fi
		escaped_val="$(printf '%s' "$val" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
		json_pairs+=("\"$key\":\"$escaped_val\"")
	fi
done <<<"${KEYS:-}"

json_out="{$(
	IFS=,
	echo "${json_pairs[*]:-}"
)}"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
	echo "json=$json_out" >>"$GITHUB_OUTPUT"
fi
