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
	if command -v jq >/dev/null 2>&1; then
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
						. + { ($k): $val_str }
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
	elif command -v python3 >/dev/null 2>&1; then
		json_out="$(python3 -c '
import json, re, sys

json_str = sys.argv[1]
keys_str = sys.argv[2]
mask_str = sys.argv[3]

if not json_str.strip() or json_str.strip() == "{}":
    print("{}")
    sys.exit(0)

if not keys_str:
    doc = json.loads(json_str)
    if mask_str == "true" and isinstance(doc, dict):
        for v in doc.values():
            s = str(v)
            if s:
                sys.stderr.write(f"::add-mask::{s}\n")
    print(json_str)
    sys.exit(0)

doc = json.loads(json_str)
keys = [k for k in re.split(r"[\r\n, \t]+", keys_str) if k]
result = {}
for k in keys:
    path = k.split(".")
    curr = doc
    found = True
    for part in path:
        if isinstance(curr, dict) and part in curr:
            curr = curr[part]
        else:
            found = False
            break
    if found and curr is not None:
        if isinstance(curr, bool):
            val_str = "true" if curr else "false"
        elif isinstance(curr, list):
            def to_s(x):
                if isinstance(x, bool):
                    return "true" if x else "false"
                return str(x)
            val_str = ",".join(to_s(x) for x in curr)
        elif isinstance(curr, dict):
            val_str = json.dumps(curr, separators=(",", ":"))
        else:
            val_str = str(curr)
        result[k] = val_str

if mask_str == "true" and result:
    for v in result.values():
        s = str(v)
        if s:
            sys.stderr.write(f"::add-mask::{s}\n")

print(json.dumps(result, separators=(",", ":")))
' "$json_input" "$req_keys" "$mask")"
	else
		echo "::error ::Neither jq nor python3 is available for JSON filtering." >&2
		return 1
	fi

	echo "$json_out"
}
