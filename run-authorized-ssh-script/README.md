# Run Authorized SSH Script (`run-authorized-ssh-script`)

Securely execute deployment and automation commands on remote hosts over SSH. Supports piping arbitrary environment variable payloads directly into remote target scripts using strict host key checking and ephemeral identity credentials.

## Usage

```yaml
- name: Execute Deployment Script over SSH
  uses: bumuellp/lights-camera-bum-action/run-authorized-ssh-script@v1
  with:
    ssh-user: deployer
    ssh-host: k8s-node1.home.arpa
    ssh-port: 22
    ssh-key-path: ${{ runner.temp }}/id_ed25519
    env-payload: "IMAGE_TAG=v1.0.2\nENV=production"
    remote-command: "/usr/local/bin/deploy-service.sh"
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `ssh-user` | Remote SSH username. | **Yes** | — |
| `ssh-host` | Remote SSH host (hostname or IP). | **Yes** | — |
| `ssh-port` | Remote SSH port. | No | `''` (defaults to 22) |
| `ssh-key-path` | Path to private SSH key file on runner. | No | `/runner_ssh_key` |
| `env-payload` | Environment payload string to pipe into remote script stdin. | No | `''` |
| `remote-command` | Command to execute on remote host. | **Yes** | — |
