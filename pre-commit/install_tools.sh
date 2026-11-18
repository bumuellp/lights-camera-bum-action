#!/usr/bin/env bash
# ==============================================================================
# Install missing linter binaries into ~/.local/bin and Python tools into venv
# ==============================================================================
set -euo pipefail

BIN_DIR="${HOME}/.local/bin"
VENV_DIR="${HOME}/.local/share/pre-commit-venv"
mkdir -p "$BIN_DIR"
export PATH="${VENV_DIR}/bin:${BIN_DIR}:${PATH}"

ARCH_RAW="$(uname -m)"
case "$ARCH_RAW" in
x86_64 | amd64)
    ARCH="amd64"
    UNAME_ARCH="x86_64"
    TRIVY_ARCH="64bit"
    ;;
aarch64 | arm64)
    ARCH="arm64"
    UNAME_ARCH="arm64"
    TRIVY_ARCH="ARM64"
    ;;
*)
    echo "::error ::Unsupported architecture: ${ARCH_RAW}" >&2
    exit 1
    ;;
esac

download_bin() {
    local url="$1"
    local name="$2"
    echo "Installing ${name}..."
    curl -fsSL --retry 3 "$url" -o "${BIN_DIR}/${name}"
    chmod +x "${BIN_DIR}/${name}"
}

download_tar_bin() {
    local url="$1"
    local member="$2"
    local name="$3"
    local tmpdir
    tmpdir="$(mktemp -d)"
    echo "Installing ${name}..."
    curl -fsSL --retry 3 "$url" | tar -xz -C "$tmpdir" "$member"
    mv "${tmpdir}/${member}" "${BIN_DIR}/${name}"
    chmod +x "${BIN_DIR}/${name}"
    rm -rf "$tmpdir"
}

download_bats() {
    local ver="${BATS_VERSION:-1.13.0}"
    ver="${ver#v}"
    local tmpdir prefix
    tmpdir="$(mktemp -d)"
    prefix="${HOME}/.local/share/bats-core"
    echo "Installing bats v${ver}..."
    curl -fsSL --retry 3 "https://github.com/bats-core/bats-core/archive/refs/tags/v${ver}.tar.gz" | tar -xz -C "$tmpdir"
    mkdir -p "$prefix"
    "${tmpdir}/bats-core-${ver}/install.sh" "$prefix" >/dev/null
    ln -sf "${prefix}/bin/bats" "${BIN_DIR}/bats"
    rm -rf "$tmpdir"
}

install_one_tool() {
    local tool="$1"
    if command -v "$tool" >/dev/null 2>&1; then
        return 0
    fi
    case "$tool" in
    shfmt)
        download_bin "https://github.com/mvdan/sh/releases/download/${SHFMT_VERSION}/shfmt_${SHFMT_VERSION}_linux_${ARCH}" shfmt
        ;;
    trufflehog)
        download_tar_bin "https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION#v}/trufflehog_${TRUFFLEHOG_VERSION#v}_linux_${ARCH}.tar.gz" trufflehog trufflehog
        ;;
    trivy)
        download_tar_bin "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION#v}/trivy_${TRIVY_VERSION#v}_Linux-${TRIVY_ARCH}.tar.gz" trivy trivy
        ;;
    tofu)
        download_tar_bin "https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION#v}/tofu_${TOFU_VERSION#v}_linux_${ARCH}.tar.gz" tofu tofu
        ;;
    hadolint)
        download_bin "https://github.com/hadolint/hadolint/releases/download/${HADOLINT_VERSION}/hadolint-Linux-${UNAME_ARCH}" hadolint
        ;;
    kubeconform)
        download_tar_bin "https://github.com/yannh/kubeconform/releases/download/${KUBECONFORM_VERSION}/kubeconform-linux-${ARCH}.tar.gz" kubeconform kubeconform
        ;;
    kube-score)
        download_tar_bin "https://github.com/zegl/kube-score/releases/download/${KUBESCORE_VERSION}/kube-score_${KUBESCORE_VERSION#v}_linux_${ARCH}.tar.gz" kube-score kube-score
        ;;
    kustomize)
        download_tar_bin "https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize%2F${KUSTOMIZE_VERSION}/kustomize_${KUSTOMIZE_VERSION}_linux_${ARCH}.tar.gz" kustomize kustomize
        ;;
    bats)
        download_bats
        ;;
    *)
        echo "::warning ::Unknown optional tool '${tool}', skipping."
        ;;
    esac
}

pids=()
for tool in ${REQUIRED_TOOLS:-}; do
    install_one_tool "$tool" &
    pids+=("$!")
done

for pid in "${pids[@]}"; do
    wait "$pid"
done

pkgs=("pre-commit==${PRE_COMMIT_VERSION}" "yamllint==${YAMLLINT_VERSION}")
if [ "${PYTEST_ENABLED:-false}" = "true" ]; then
    command -v pytest >/dev/null 2>&1 || pkgs+=("pytest")
    command -v uv >/dev/null 2>&1 || pkgs+=("uv")
fi
if [ "${ANSIBLE_ENABLED:-false}" = "true" ]; then
    pkgs+=("ansible-core" "ansible-lint")
fi

pkg_stamp="${pkgs[*]}"
marker_file="${VENV_DIR}/.installed-versions"
if [ ! -x "${VENV_DIR}/bin/pre-commit" ] || [ ! -f "$marker_file" ] || [ "$(cat "$marker_file")" != "$pkg_stamp" ]; then
    echo "Installing Python lint tools (${pkg_stamp})..."
    python3 -m venv "$VENV_DIR"
    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "${VENV_DIR}/bin/python" --quiet "${pkgs[@]}"
    else
        "${VENV_DIR}/bin/pip" install --quiet --no-cache-dir "${pkgs[@]}"
    fi
    printf '%s' "$pkg_stamp" >"$marker_file"
fi
