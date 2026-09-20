#!/usr/bin/env bash
# Execute remote command with piped environment payload over SSH
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common/ssh-common.sh
source "${SCRIPT_DIR}/../common/ssh-common.sh"

setup_ssh_env

REMOTE_COMMAND="${REMOTE_COMMAND:?REMOTE_COMMAND is required}"
ENV_PAYLOAD="${ENV_PAYLOAD:-}"

printf '%s' "$ENV_PAYLOAD" | ssh "${ssh_args[@]}" "$remote" -- "$REMOTE_COMMAND"
