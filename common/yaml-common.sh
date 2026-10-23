#!/usr/bin/env bash
# ==============================================================================
# Shared JSON extraction and masking helper for YAML/JSON configurations
# Used by parse-config and decrypt-sops
# ==============================================================================
set -euo pipefail

filter_json_keys() {
	local json_input="$1"
	local req_keys="${2:-}"
	local mask="${3:-false}"

	if [ -z "$json_input" ] || [ "$json_input" = "{}" ]; then
		echo "{}"
		return 0
	fi

	local json_out
	if [ -n "$req_keys" ]; then
		json_out="$(echo "$json_input" | jq --arg keys "$req_keys" -c '
			. as $doc |
			reduce ($keys | split("[\r\n, \t]+"; "") | map(select(length > 0))[]) as $k ({};
				($k | split(".")) as $path |
				($doc | getpath($path)) as $val |
				if $val != null then
					(
						if ($val | type) == "array" then
							($val | map(tostring) | join(","))
						elif ($val | type) == "object" then
							($val | tojson)
						else
							($val | tostring)
						end
					) as $val_str |
					. + { ($k): $val_str } + (if ($k | contains(".")) then { ($k | gsub("\\."; "_")): $val_str } else {} end)
				else
					.
				end
			)
		')"
	else
		json_out="$json_input"
	fi

	if [ "$mask" = "true" ] && [ "$json_out" != "{}" ]; then
		while IFS= read -r val; do
			if [ -n "$val" ]; then
				echo "::add-mask::$val" >&2
			fi
		done < <(echo "$json_out" | jq -r 'to_entries[].value | tostring')
	fi

	echo "$json_out"
}
