#!/usr/bin/env bash
# ==============================================================================
# Detect which linter binaries are required by .pre-commit-config.yaml
# ==============================================================================
set -euo pipefail

WORKSPACE="${GITHUB_WORKSPACE:-.}"
CONFIG_FILE="${WORKSPACE}/.pre-commit-config.yaml"

tools=()
trivy_enabled="false"
ansible_enabled="false"
pytest_enabled="false"

has_hook() {
    local pattern="$1"
    grep -qE "$pattern" "$CONFIG_FILE"
}

if [ -f "$CONFIG_FILE" ]; then
    has_hook 'id:\s*secret-scan' && tools+=("trufflehog")
    has_hook 'id:\s*shell-lint' && tools+=("shfmt")
    has_hook 'id:\s*shell-tests' && tools+=("bats")
    if has_hook 'id:\s*(trivy-config|trivy-fs|trivy-security)'; then
        tools+=("trivy")
        trivy_enabled="true"
    fi
    has_hook 'id:\s*tofu-fmt' && tools+=("tofu")
    if has_hook 'id:\s*(docker-lint|hadolint)'; then
        tools+=("hadolint")
    fi
    if has_hook 'id:\s*k8s-validate'; then
        tools+=("kubeconform" "kube-score" "kustomize")
    fi
    has_hook 'id:\s*ansible-lint' && ansible_enabled="true"
    has_hook 'id:\s*python-tests' && pytest_enabled="true"
fi

tools_str="${tools[*]-}"
key_material="$(printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s' \
    "$tools_str" \
    "$ansible_enabled" \
    "$pytest_enabled" \
    "${PRE_COMMIT_VERSION:-}" \
    "${YAMLLINT_VERSION:-}" \
    "${SHFMT_VERSION:-}" \
    "${TRUFFLEHOG_VERSION:-}" \
    "${TRIVY_VERSION:-}" \
    "${TOFU_VERSION:-}" \
    "${HADOLINT_VERSION:-}" \
    "${KUBECONFORM_VERSION:-}" \
    "${KUBESCORE_VERSION:-}" \
    "${KUSTOMIZE_VERSION:-}")"

tools_hash="$(printf '%s' "$key_material" | sha256sum | cut -c1-16)"
trivy_db_week="$(date -u +%Y-%W)"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    {
        echo "tools=${tools_str}"
        echo "trivy_enabled=${trivy_enabled}"
        echo "ansible_enabled=${ansible_enabled}"
        echo "pytest_enabled=${pytest_enabled}"
        echo "tools_hash=${tools_hash}"
        echo "trivy_db_week=${trivy_db_week}"
    } >>"$GITHUB_OUTPUT"
fi

echo "Detected tools: ${tools_str:-none} (ansible=${ansible_enabled}, pytest=${pytest_enabled}, trivy=${trivy_enabled})"
