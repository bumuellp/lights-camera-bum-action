#!/usr/bin/env bash
# ==============================================================================
# sync-dns-record: Provider-agnostic DNS manager (deSEC & IONOS)
# ==============================================================================
set -euo pipefail

PROVIDER="${DNS_PROVIDER:-desec}"
TOKEN="${DNS_TOKEN:-}"
DOMAIN="${DNS_DOMAIN:-}"
SUBNAME="${DNS_SUBNAME:-}"
RECORD_TYPE="${DNS_TYPE:-A}"
RECORDS_RAW="${DNS_RECORDS:-}"
TTL="${DNS_TTL:-60}"
ACTION="${DNS_ACTION:-sync}"

if [ -n "$TOKEN" ]; then
	echo "::add-mask::$TOKEN"
fi

if [ -z "$TOKEN" ]; then
	echo "ERROR: DNS API token (token / DNS_TOKEN) must be provided." >&2
	exit 1
fi

if [ -z "$DOMAIN" ]; then
	echo "ERROR: DNS domain (domain / DNS_DOMAIN) must be provided." >&2
	exit 1
fi

PROVIDER="$(echo "$PROVIDER" | tr '[:upper:]' '[:lower:]')"
RECORD_TYPE="$(echo "$RECORD_TYPE" | tr '[:lower:]' '[:upper:]')"
ACTION="$(echo "$ACTION" | tr '[:upper:]' '[:lower:]')"

# Normalize subname ('@' means root domain)
if [ "$SUBNAME" = "@" ]; then
	SUBNAME=""
fi

# Compute FQDN
if [ -z "$SUBNAME" ]; then
	FQDN="$DOMAIN"
else
	FQDN="${SUBNAME}.${DOMAIN}"
fi

# Helper: parse records to JSON array string
parse_records_json() {
	python3 -c "
import json
raw = '''${RECORDS_RAW}'''.strip()
if raw.startswith('[') and raw.endswith(']'):
    try:
        parsed = json.loads(raw)
        records = [str(r).strip() for r in parsed if str(r).strip()]
    except Exception:
        records = [r.strip().strip('\"\'') for r in raw.strip('[]').split(',') if r.strip()]
else:
    records = [r.strip() for r in raw.replace(',', ' ').split() if r.strip()]

print(json.dumps(records))
"
}

# ------------------------------------------------------------------------------
# 1. deSEC.io Provider Implementation
# ------------------------------------------------------------------------------
sync_desec() {
	local api_base="https://desec.io/api/v1/domains/${DOMAIN}/rrsets"
	local payload=""

	if [ "$ACTION" = "delete" ]; then
		echo "Deleting deSEC RRset: subname='${SUBNAME}', type='${RECORD_TYPE}' for domain '${DOMAIN}'..."
		payload="$(python3 -c "
import json
print(json.dumps([{'subname': '${SUBNAME}', 'type': '${RECORD_TYPE}', 'records': [], 'ttl': int('${TTL}')}]))
")"
	elif [ "$ACTION" = "sync" ]; then
		if [ -z "$RECORDS_RAW" ]; then
			echo "ERROR: records must be specified when action is 'sync'." >&2
			exit 1
		fi
		echo "Syncing deSEC RRset: ${FQDN} (${RECORD_TYPE}) -> '${RECORDS_RAW}' (TTL ${TTL})..."
		local rec_json
		rec_json="$(parse_records_json)"
		payload="$(python3 -c "
import json
records = ${rec_json}
print(json.dumps([{'subname': '${SUBNAME}', 'type': '${RECORD_TYPE}', 'records': records, 'ttl': int('${TTL}')}]))
")"
	else
		echo "ERROR: Unsupported action '${ACTION}'. Allowed: sync, delete." >&2
		exit 1
	fi

	local response_file
	response_file="$(mktemp)"
	local http_code
	http_code="$(curl -sS -w "%{http_code}" -o "$response_file" \
		-X PATCH "${api_base}/" \
		-H "Authorization: Token ${TOKEN}" \
		-H "Content-Type: application/json" \
		-H "Accept: application/json" \
		--data "$payload")"

	if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
		echo "Successfully updated deSEC DNS record (HTTP ${http_code})."
		rm -f "$response_file"
	else
		echo "ERROR: deSEC API returned HTTP ${http_code}:" >&2
		cat "$response_file" >&2
		echo "" >&2
		rm -f "$response_file"
		exit 1
	fi
}

# ------------------------------------------------------------------------------
# 2. IONOS Domain API Provider Implementation
# ------------------------------------------------------------------------------
sync_ionos() {
	local api_base="https://api.hosting.ionos.com/dns/v1"

	# 1. Look up Zone ID for the domain
	echo "Looking up IONOS Zone ID for '${DOMAIN}'..."
	local zones_file
	zones_file="$(mktemp)"
	local http_code
	http_code="$(curl -sS -w "%{http_code}" -o "$zones_file" \
		-X GET "${api_base}/zones" \
		-H "X-API-Key: ${TOKEN}" \
		-H "Accept: application/json")"

	if [ "$http_code" -ne 200 ]; then
		echo "ERROR: Failed to retrieve IONOS zones (HTTP ${http_code}):" >&2
		cat "$zones_file" >&2
		rm -f "$zones_file"
		exit 1
	fi

	local zone_id
	zone_id="$(python3 -c "
import json, sys
try:
    with open('${zones_file}', 'r') as f:
        zones = json.load(f)
    matching = [z['id'] for z in zones if z.get('name', '').lower() == '${DOMAIN}'.lower()]
    if matching:
        print(matching[0])
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)
" || true)"
	rm -f "$zones_file"

	if [ -z "$zone_id" ]; then
		echo "ERROR: Could not find IONOS zone matching domain '${DOMAIN}'." >&2
		exit 1
	fi
	echo "Found IONOS Zone ID: ${zone_id}"

	# 2. Query existing records in zone
	local query_file
	query_file="$(mktemp)"
	http_code="$(curl -sS -w "%{http_code}" -o "$query_file" \
		-X GET "${api_base}/zones/${zone_id}?recordName=${FQDN}&recordType=${RECORD_TYPE}" \
		-H "X-API-Key: ${TOKEN}" \
		-H "Accept: application/json")"

	if [ "$http_code" -ne 200 ]; then
		echo "ERROR: Failed to query existing records in IONOS zone (HTTP ${http_code}):" >&2
		cat "$query_file" >&2
		rm -f "$query_file"
		exit 1
	fi

	local existing_records_file
	existing_records_file="$(mktemp)"
	python3 -c "
import json
with open('${query_file}', 'r') as f:
    data = json.load(f)
records = data.get('records', [])
matching = [r for r in records if r.get('name', '').lower() == '${FQDN}'.lower() and r.get('type', '').upper() == '${RECORD_TYPE}'.upper()]
with open('${existing_records_file}', 'w') as out:
    json.dump(matching, out)
"
	rm -f "$query_file"

	if [ "$ACTION" = "delete" ]; then
		echo "Deleting matching IONOS records for ${FQDN} (${RECORD_TYPE})..."
		local rec_ids
		rec_ids="$(python3 -c "
import json
with open('${existing_records_file}', 'r') as f:
    recs = json.load(f)
for r in recs:
    print(r.get('id', ''))
")"
		for rid in $rec_ids; do
			[ -z "$rid" ] && continue
			echo "Deleting record ID: $rid"
			curl -sS -X DELETE "${api_base}/zones/${zone_id}/records/${rid}" \
				-H "X-API-Key: ${TOKEN}" \
				-H "Accept: application/json" >/dev/null || true
		done
		echo "IONOS DNS record(s) deleted successfully."
		rm -f "$existing_records_file"
		return 0
	elif [ "$ACTION" = "sync" ]; then
		if [ -z "$RECORDS_RAW" ]; then
			echo "ERROR: records must be specified when action is 'sync'." >&2
			rm -f "$existing_records_file"
			exit 1
		fi

		local rec_json
		rec_json="$(parse_records_json)"
		local first_value
		first_value="$(python3 -c "
import json
recs = ${rec_json}
print(recs[0] if recs else '')
")"

		local existing_count
		existing_count="$(python3 -c "
import json
with open('${existing_records_file}', 'r') as f:
    recs = json.load(f)
print(len(recs))
")"

		if [ "$existing_count" -gt 0 ]; then
			local existing_id
			existing_id="$(python3 -c "
import json
with open('${existing_records_file}', 'r') as f:
    recs = json.load(f)
print(recs[0]['id'])
")"
			echo "Updating existing IONOS record ${existing_id} for ${FQDN} -> ${first_value}..."
			local put_body
			put_body="$(python3 -c "
import json
print(json.dumps({'name': '${FQDN}', 'type': '${RECORD_TYPE}', 'content': '${first_value}', 'ttl': int('${TTL}'), 'prio': 0, 'disabled': False}))
")"
			local resp
			resp="$(mktemp)"
			http_code="$(curl -sS -w "%{http_code}" -o "$resp" \
				-X PUT "${api_base}/zones/${zone_id}/records/${existing_id}" \
				-H "X-API-Key: ${TOKEN}" \
				-H "Content-Type: application/json" \
				--data "$put_body")"
			if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
				echo "Successfully updated IONOS record (HTTP ${http_code})."
			else
				echo "ERROR: Failed to update IONOS record (HTTP ${http_code}):" >&2
				cat "$resp" >&2
				rm -f "$resp" "$existing_records_file"
				exit 1
			fi
			rm -f "$resp"
		else
			echo "Creating new IONOS record for ${FQDN} -> ${first_value}..."
			local post_body
			post_body="$(python3 -c "
import json
print(json.dumps([{'name': '${FQDN}', 'type': '${RECORD_TYPE}', 'content': '${first_value}', 'ttl': int('${TTL}'), 'prio': 0, 'disabled': False}]))
")"
			local resp
			resp="$(mktemp)"
			http_code="$(curl -sS -w "%{http_code}" -o "$resp" \
				-X POST "${api_base}/zones/${zone_id}/records" \
				-H "X-API-Key: ${TOKEN}" \
				-H "Content-Type: application/json" \
				--data "$post_body")"
			if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
				echo "Successfully created IONOS record (HTTP ${http_code})."
			else
				echo "ERROR: Failed to create IONOS record (HTTP ${http_code}):" >&2
				cat "$resp" >&2
				rm -f "$resp" "$existing_records_file"
				exit 1
			fi
			rm -f "$resp"
		fi
		rm -f "$existing_records_file"
	fi
}

# ------------------------------------------------------------------------------
# Dispatcher
# ------------------------------------------------------------------------------
case "$PROVIDER" in
desec)
	sync_desec
	;;
ionos)
	sync_ionos
	;;
*)
	echo "ERROR: Unsupported DNS provider '${PROVIDER}'. Supported: 'desec', 'ionos'." >&2
	exit 1
	;;
esac
