#!/usr/bin/env bash
# ==============================================================================
# Install mise (if needed) and activate/install discovered tool specifications
# ==============================================================================
set -euo pipefail

export PATH="${HOME}/.local/share/mise/shims:${HOME}/.local/bin:${PATH}"

if ! command -v mise >/dev/null 2>&1; then
    echo "Installing mise..."
    mkdir -p "${HOME}/.local/bin"
    curl -fsSL --retry 3 https://mise.run | MISE_INSTALL_PATH="${HOME}/.local/bin/mise" sh
fi

WORKSPACE="${GITHUB_WORKSPACE:-.}"
cd "$WORKSPACE"

# Trust and install repo-level mise configuration if present
if [ -f "mise.toml" ] || [ -f ".mise.toml" ] || [ -f ".tool-versions" ] || [ -f ".mise/config.toml" ]; then
    mise trust --all --yes >/dev/null 2>&1 || mise trust --all >/dev/null 2>&1 || true
    mise install --yes
fi

# Install hook-declared and input tool specs
if [ -n "${REQUIRED_TOOLS:-}" ]; then
    STATE_DIR="${HOME}/.local/share/mise"
    MARKER_FILE="${STATE_DIR}/.installed-tools"
    if [ -f "$MARKER_FILE" ] && [ "$(cat "$MARKER_FILE")" = "$REQUIRED_TOOLS" ] && [ -f "${HOME}/.config/mise/config.toml" ]; then
        echo "Discovered mise tools already cached: ${REQUIRED_TOOLS}"
        exit 0
    fi

    read -r -a all_tools <<<"$REQUIRED_TOOLS"
    uv_tools=()
    other_tools=()
    needs_uv="false"

    for spec in "${all_tools[@]}"; do
        case "$spec" in
        uv | uv@*)
            uv_tools+=("$spec")
            ;;
        pipx:* | pypi:*)
            needs_uv="true"
            other_tools+=("$spec")
            ;;
        *)
            other_tools+=("$spec")
            ;;
        esac
    done

    if [ "${#uv_tools[@]}" -gt 0 ]; then
        mise use --global --yes "${uv_tools[@]}"
    elif [ "$needs_uv" = "true" ] && ! command -v uv >/dev/null 2>&1; then
        mise use --global --yes uv@latest
    fi

    if [ "${#other_tools[@]}" -gt 0 ]; then
        mise use --global --yes "${other_tools[@]}"
    fi

    mkdir -p "$STATE_DIR"
    printf '%s' "$REQUIRED_TOOLS" >"$MARKER_FILE"
fi
