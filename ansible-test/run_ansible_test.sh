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

COLLECTIONS_PATH="${ANSIBLE_COLLECTIONS_PATH:-${HOME}/.ansible/collections}"
mkdir -p "$COLLECTIONS_PATH"
export ANSIBLE_COLLECTIONS_PATH="$COLLECTIONS_PATH"

build_dir=""
trap 'if [ -n "${build_dir:-}" ] && [ -d "$build_dir" ]; then rm -rf "$build_dir"; fi' EXIT

if [ -n "$GALAXY_FILE" ] && [ -f "$GALAXY_FILE" ]; then
	build_dir="$(mktemp -d)"
	galaxy_dir="$(dirname "$GALAXY_FILE")"
	echo "=== Building collection from $galaxy_dir ==="
	ansible-galaxy collection build --force --output-path "$build_dir" "$galaxy_dir"
	tarballs=("$build_dir"/*.tar.gz)
	if [ "${#tarballs[@]}" -eq 0 ]; then
		echo "ERROR: collection build produced no tarball" >&2
		exit 1
	fi
	ansible-galaxy collection install --force "${tarballs[0]}" -p "$COLLECTIONS_PATH"
fi

if [ -n "$REQUIREMENTS_FILE" ] && [ -f "$REQUIREMENTS_FILE" ]; then
	echo "=== Installing collections from $REQUIREMENTS_FILE ==="
	ansible-galaxy collection install -r "$REQUIREMENTS_FILE" -p "$COLLECTIONS_PATH"
fi

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

read -r -a patterns <<<"$PLAYBOOKS_GLOB"
declare -A seen=()
playbooks=()
for pattern in "${patterns[@]}"; do
	# shellcheck disable=SC2206
	matches=($pattern)
	for pb in "${matches[@]}"; do
		[ -f "$pb" ] || continue
		if [ -z "${seen[$pb]:-}" ]; then
			seen[$pb]=1
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
