# Sync Path via Rsync (`sync-rsync-path`)

Synchronize local repository directories and artifacts to remote hosts over SSH using `rsync`. Pre-creates remote destination directories safely, respects exclusion lists, and leverages standard SSH authentication keys.

## Usage

```yaml
- name: Sync Static Assets to Remote Host
  uses: bumuellp/lights-camera-bum-action/sync-rsync-path@v1
  with:
    ssh-user: deployer
    ssh-host: storage.home.arpa
    ssh-port: 22
    ssh-key-path: ${{ runner.temp }}/id_ed25519
    local-path: ./dist
    remote-directory: /var/www/portal
    rsync-args: '-avz --delete'
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `ssh-user` | Remote SSH username. | **Yes** | — |
| `ssh-host` | Remote SSH host. | **Yes** | — |
| `ssh-port` | Remote SSH port. | No | `''` (defaults to 22) |
| `ssh-key-path` | Path to private SSH key file on runner. | No | `/runner_ssh_key` |
| `local-path` | Local directory or file to synchronize. | **Yes** | — |
| `remote-directory` | Remote target destination directory. | **Yes** | — |
| `exclude-from` | Optional path to rsync exclude rules file. | No | `''` |
| `rsync-args` | Extra flags passed to `rsync`. | No | `'-avz --delete'` |
