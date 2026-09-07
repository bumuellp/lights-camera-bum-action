#!/usr/bin/env bash
# Sync path via rsync over SSH
set -euo pipefail

SSH_USER="${SSH_USER:?SSH_USER is required}"
SSH_HOST="${SSH_HOST:?SSH_HOST is required}"
REMOTE_DIRECTORY="${REMOTE_DIRECTORY:?REMOTE_DIRECTORY is required}"
LOCAL_PATH="${LOCAL_PATH:?LOCAL_PATH is required}"
EXCLUDE_FROM="${EXCLUDE_FROM:-}"
RSYNC_ARGS="${RSYNC_ARGS:--avz --delete}"
SSH_KEY_PATH="${SSH_KEY_PATH:-/runner_ssh_key}"
SSH_PORT="${SSH_PORT:-}"

remote="${SSH_USER}@${SSH_HOST}"
ssh_args=(-i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no)
ssh_transport="ssh -i $SSH_KEY_PATH -o StrictHostKeyChecking=no"

if [ -n "$SSH_PORT" ]; then
	ssh_args+=(-p "$SSH_PORT")
	ssh_transport="$ssh_transport -p $SSH_PORT"
fi

ssh "${ssh_args[@]}" "$remote" -- "mkdir -p '$REMOTE_DIRECTORY'"

if [ -n "$EXCLUDE_FROM" ]; then
	exclude_relative="$(basename "$EXCLUDE_FROM")"
	if [[ "$EXCLUDE_FROM" == "$LOCAL_PATH"* ]]; then
		exclude_relative="${EXCLUDE_FROM#"$LOCAL_PATH"/}"
	fi
	remote_exclude_target="$REMOTE_DIRECTORY/$exclude_relative"
	remote_exclude_parent="$(dirname "$remote_exclude_target")"

	ssh "${ssh_args[@]}" "$remote" -- "mkdir -p '$remote_exclude_parent'"
	rsync -a -e "$ssh_transport" "$EXCLUDE_FROM" "$remote:$remote_exclude_target"
fi

read -r -a rsync_extra_args <<<"$RSYNC_ARGS"
rsync_command=(rsync "${rsync_extra_args[@]}")
if [ -n "$EXCLUDE_FROM" ]; then
	rsync_command+=(--exclude-from="$EXCLUDE_FROM")
fi
rsync_command+=(-e "$ssh_transport")
rsync_command+=("$LOCAL_PATH" "$remote:$REMOTE_DIRECTORY/")

"${rsync_command[@]}"
