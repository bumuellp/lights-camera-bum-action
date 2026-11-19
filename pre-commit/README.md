# Pre-Commit Validation & Testing (`pre-commit`)

Run pre-commit hooks natively on the runner with cached hook environments, `mise` runtime support (for project `mise.toml` / `.tool-versions` / self-contained hooks), and optional `lint-tools` container fallback.

## Usage

```yaml
- name: Run Pre-Commit & Tests
  uses: bumuellp/lights-camera-bum-action/pre-commit@v1
  with:
    extra-args: '--all-files --show-diff-on-failure'
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `extra-args` | Additional arguments to pass to `pre-commit run`. | No | `'--all-files'` |
| `tools` | Optional `mise` tool specs to preinstall (e.g. `trivy@0.75.0`). | No | `''` |
| `cache` | Enable `actions/cache@v6` for venv, hook envs, `mise` tools, and Trivy DB. | No | `'true'` |
| `pre-commit-version` | Pinned `pre-commit` version (tracked by Renovate). | No | `'4.6.2'` |
| `use-container` | Run inside `lint-tools` container instead of natively. | No | `'false'` |
| `container-image` | Container image used when `use-container: 'true'`. | No | `ghcr.io/bumuellp/lint-tools:v1.4.1@...` |
