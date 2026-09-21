#!/usr/bin/env bash
# ==============================================================================
# Shared SSH Configuration and Transport Setup
# Used by run-authorized-ssh-script and sync-rsync-path
# ==============================================================================
set -euo pipefail

setup_ssh_env() {
	SSH_USER="${SSH_USER:?SSH_USER is required}"
	SSH_HOST="${SSH_HOST:?SSH_HOST is required}"
	SSH_KEY_PATH="${SSH_KEY_PATH:-/runner_ssh_key}"
	SSH_PORT="${SSH_PORT:-}"

	export remote="${SSH_USER}@${SSH_HOST}"
	ssh_args=(-i "$SSH_KEY_PATH" -o StrictHostKeyChecking=accept-new)
	ssh_transport="ssh -i '$SSH_KEY_PATH' -o StrictHostKeyChecking=accept-new"

	if [ -n "$SSH_PORT" ]; then
		ssh_args+=(-p "$SSH_PORT")
		ssh_transport="$ssh_transport -p $SSH_PORT"
	fi
}
