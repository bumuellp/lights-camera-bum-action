#!/usr/bin/env bash
# Sync path via rsync over SSH
set -euo pipefail

remote="${SSH_USER}@${SSH_HOST}"
remote_directory="${REMOTE_DIRECTORY}"
local_path="${LOCAL_PATH}"
exclude_from="${EXCLUDE_FROM:-}"
rsync_args="${RSYNC_ARGS:--avz --delete}"
key_path="${SSH_KEY_PATH:-/runner_ssh_key}"

ssh_args=(-i "$key_path" -o StrictHostKeyChecking=no)
ssh_transport="ssh -i $key_path -o StrictHostKeyChecking=no"

if [ -n "${SSH_PORT:-}" ]; then
	ssh_args+=(-p "${SSH_PORT}")
	ssh_transport="$ssh_transport -p ${SSH_PORT}"
fi

ssh "${ssh_args[@]}" "$remote" "mkdir -p '$remote_directory'"

if [ -n "$exclude_from" ]; then
	exclude_relative="$(basename "$exclude_from")"
	if [[ "$exclude_from" == "$local_path"* ]]; then
		exclude_relative="${exclude_from#"$local_path"/}"
	fi
	remote_exclude_target="$remote_directory/$exclude_relative"
	remote_exclude_parent="$(dirname "$remote_exclude_target")"

	ssh "${ssh_args[@]}" "$remote" "mkdir -p '$remote_exclude_parent'"
	rsync -a -e "$ssh_transport" "$exclude_from" "$remote:$remote_exclude_target"
fi

rsync_command=(rsync)
if [ -n "$exclude_from" ]; then
	rsync_command+=(--exclude-from="$exclude_from")
fi
if [ -n "$rsync_args" ]; then
	# shellcheck disable=SC2206
	rsync_command+=($rsync_args)
fi
rsync_command+=(-e "$ssh_transport")
rsync_command+=("$local_path" "$remote:$remote_directory/")

"${rsync_command[@]}"
