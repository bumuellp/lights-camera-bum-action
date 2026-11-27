#!/usr/bin/env bash
# ==============================================================================
# Build/install the local collection and syntax-check discovered playbooks
# ==============================================================================
set -euo pipefail
shopt -s nullglob

PLAYBOOKS_GLOB="${PLAYBOOKS_GLOB:-playbooks/*.yml tests/*playbook*.yml}"
INVENTORY="${INVENTORY-tests/inventory.ini}"
GALAXY_FILE="${GALAXY_FILE-galaxy.yml}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE-requirements.yml}"
RUN_LINT="${RUN_LINT:-false}"

VENV_DIR="${ANSIBLE_VENV_DIR:-${HOME}/.local/share/ansible-test-venv}"
if [ -d "${VENV_DIR}/bin" ]; then
	export PATH="${VENV_DIR}/bin:${PATH}"
fi

COLLECTIONS_DIR="${ANSIBLE_TEST_COLLECTIONS_DIR:-${HOME}/.ansible/collections}"
mkdir -p "$COLLECTIONS_DIR"

build_dir=""
local_collections_dir=""
trap 'if [ -n "${build_dir:-}" ] && [ -d "$build_dir" ]; then rm -rf "$build_dir"; fi' EXIT

if [ -n "$GALAXY_FILE" ] && [ -f "$GALAXY_FILE" ]; then
	build_dir="$(mktemp -d)"
	local_collections_dir="${build_dir}/collections"
	mkdir -p "$local_collections_dir"

	py_bin="python3"
	if [ -x "${VENV_DIR}/bin/python" ]; then
		py_bin="${VENV_DIR}/bin/python"
	fi
	deps_req="${build_dir}/galaxy-deps.yml"
	GALAXY_FILE="$GALAXY_FILE" DEPS_REQ="$deps_req" "$py_bin" -c '
import os, yaml
with open(os.environ["GALAXY_FILE"], encoding="utf-8") as fh:
    data = yaml.safe_load(fh) or {}
deps = data.get("dependencies") or {}
if deps:
    items = [{"name": k, "version": str(v)} for k, v in deps.items()]
    with open(os.environ["DEPS_REQ"], "w", encoding="utf-8") as out:
        yaml.safe_dump({"collections": items}, out)
'
	if [ -s "$deps_req" ]; then
		echo "=== Installing collection dependencies from $GALAXY_FILE ==="
		ansible-galaxy collection install --upgrade -r "$deps_req" -p "$COLLECTIONS_DIR"
	fi

	galaxy_dir="$(dirname "$GALAXY_FILE")"
	echo "=== Building collection from $galaxy_dir ==="
	ansible-galaxy collection build --force --output-path "$build_dir" "$galaxy_dir"
	tarballs=("$build_dir"/*.tar.gz)
	if [ "${#tarballs[@]}" -eq 0 ]; then
		echo "ERROR: collection build produced no tarball" >&2
		exit 1
	fi
	ansible-galaxy collection install --no-deps --force "${tarballs[0]}" -p "$local_collections_dir"
fi

if [ -n "$REQUIREMENTS_FILE" ] && [ -f "$REQUIREMENTS_FILE" ]; then
	echo "=== Installing collections from $REQUIREMENTS_FILE ==="
	ansible-galaxy collection install --upgrade -r "$REQUIREMENTS_FILE" -p "$COLLECTIONS_DIR"
fi

joined_paths=()
[ -n "$local_collections_dir" ] && joined_paths+=("$local_collections_dir")
joined_paths+=("$COLLECTIONS_DIR")
if [ -n "${ANSIBLE_COLLECTIONS_PATH:-}" ]; then
	joined_paths+=("$ANSIBLE_COLLECTIONS_PATH")
fi
ANSIBLE_COLLECTIONS_PATH="$(
	IFS=:
	printf '%s' "${joined_paths[*]}"
)"
export ANSIBLE_COLLECTIONS_PATH

if [ "$RUN_LINT" = "true" ]; then
	echo "=== Running yamllint ==="
	yamllint .
	echo "=== Running ansible-lint ==="
	ansible-lint
fi

inv_args=()
if [ -n "$INVENTORY" ]; then
	if [ ! -f "$INVENTORY" ]; then
		echo "ERROR: Inventory file not found: $INVENTORY" >&2
		exit 1
	fi
	inv_args=(-i "$INVENTORY")
fi

already_seen() {
	local target="$1"
	shift || true
	local item
	for item in "$@"; do
		[ "$item" = "$target" ] && return 0
	done
	return 1
}

IFS=$' \t\n' read -r -d '' -a patterns <<<"$PLAYBOOKS_GLOB" || true
playbooks=()
for pattern in "${patterns[@]}"; do
	# shellcheck disable=SC2206
	matches=($pattern)
	for pb in "${matches[@]}"; do
		[ -f "$pb" ] || continue
		if ! already_seen "$pb" "${playbooks[@]+${playbooks[@]}}"; then
			playbooks+=("$pb")
		fi
	done
done

if [ "${#playbooks[@]}" -eq 0 ]; then
	echo "ERROR: No playbooks found matching: $PLAYBOOKS_GLOB" >&2
	exit 1
fi

for pb in "${playbooks[@]}"; do
	echo "=== Syntax-checking $pb ==="
	ansible-playbook "${inv_args[@]}" "$pb" --syntax-check
done
