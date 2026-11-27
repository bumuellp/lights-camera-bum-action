#!/usr/bin/env bash
# ==============================================================================
# Ensure isolated ansible-core (and optional lint) Python environment exists
# ==============================================================================
set -euo pipefail

VENV_DIR="${ANSIBLE_VENV_DIR:-${HOME}/.local/share/ansible-test-venv}"
RUN_LINT="${RUN_LINT:-false}"
MARKER_FILE="${VENV_DIR}/.installed-spec"

py_ver="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
pkgs=("ansible-core==${ANSIBLE_CORE_VERSION:-2.21.4}")
required_bins=(ansible-playbook ansible-galaxy)
if [ "$RUN_LINT" = "true" ]; then
	pkgs+=("ansible-lint==${ANSIBLE_LINT_VERSION:-26.8.0}" "yamllint==${YAMLLINT_VERSION:-1.37.1}")
	required_bins+=(ansible-lint yamllint)
fi
spec="py${py_ver} ${pkgs[*]}"

installed=true
for bin in "${required_bins[@]}"; do
	[ -x "${VENV_DIR}/bin/${bin}" ] || installed=false
done

if [ "$installed" = "true" ] && [ -f "$MARKER_FILE" ] && [ "$(cat "$MARKER_FILE")" = "$spec" ]; then
	echo "Ansible environment already installed: ${spec}"
	exit 0
fi

echo "Installing ${spec} into ${VENV_DIR}..."
python3 -m venv --clear "$VENV_DIR"
if command -v uv >/dev/null 2>&1; then
	uv pip install --python "${VENV_DIR}/bin/python" --quiet "${pkgs[@]}"
else
	"${VENV_DIR}/bin/pip" install --quiet --no-cache-dir "${pkgs[@]}"
fi
printf '%s' "$spec" >"$MARKER_FILE"
