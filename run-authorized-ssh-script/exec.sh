#!/usr/bin/env bash
# Execute remote command with piped environment payload over SSH
set -euo pipefail

SSH_USER="${SSH_USER:?SSH_USER is required}"
SSH_HOST="${SSH_HOST:?SSH_HOST is required}"
REMOTE_COMMAND="${REMOTE_COMMAND:?REMOTE_COMMAND is required}"
ENV_PAYLOAD="${ENV_PAYLOAD:-}"
SSH_KEY_PATH="${SSH_KEY_PATH:-/runner_ssh_key}"
SSH_PORT="${SSH_PORT:-}"

remote="${SSH_USER}@${SSH_HOST}"
ssh_args=(-i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no)

if [ -n "$SSH_PORT" ]; then
	ssh_args+=(-p "$SSH_PORT")
fi

printf '%s' "$ENV_PAYLOAD" | ssh "${ssh_args[@]}" "$remote" -- "$REMOTE_COMMAND"
