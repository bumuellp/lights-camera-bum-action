#!/usr/bin/env bash
# Execute remote command with piped environment payload over SSH
set -euo pipefail

remote="${SSH_USER}@${SSH_HOST}"
remote_command="${REMOTE_COMMAND}"
env_payload="${ENV_PAYLOAD:-}"
key_path="${SSH_KEY_PATH:-/runner_ssh_key}"

ssh_args=(-i "$key_path" -o StrictHostKeyChecking=no)

if [ -n "${SSH_PORT:-}" ]; then
	ssh_args+=(-p "${SSH_PORT}")
fi

printf '%s' "$env_payload" | ssh "${ssh_args[@]}" "$remote" "$remote_command"
