# `ansible-test`

Composite GitHub Action that installs a pinned `ansible-core` into a cached virtualenv, builds and installs the local collection (when `galaxy.yml` exists) plus any Galaxy dependencies (`requirements.yml`), optionally runs `yamllint` + `ansible-lint`, and runs `ansible-playbook --syntax-check` on every playbook matching the configured globs. Both the Python virtualenv and installed Galaxy collections are cached via `actions/cache`.

## Inputs

| Input | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `playbooks-glob` | No | `playbooks/*.yml tests/*playbook*.yml` | Space-separated glob pattern(s) of playbooks to syntax-check. |
| `inventory` | No | `tests/inventory.ini` | Inventory file for `ansible-playbook` (empty to omit `-i`). |
| `galaxy-file` | No | `galaxy.yml` | If the file exists, build and install the collection (empty to skip). |
| `requirements-file` | No | `requirements.yml` | If the file exists, install its collections (empty to skip). |
| `ansible-core-version` | No | `2.21.4` | Pinned `ansible-core` version. |
| `ansible-lint-version` | No | `26.8.0` | Pinned `ansible-lint` version (when `run-lint` is `'true'`). |
| `yamllint-version` | No | `1.37.1` | Pinned `yamllint` version (when `run-lint` is `'true'`). |
| `run-lint` | No | `'false'` | Also run `yamllint` and `ansible-lint`. |
| `cache` | No | `'true'` | Cache the virtualenv and `~/.ansible/collections`. |

## Usage

```yaml
- uses: actions/checkout@v7
- uses: bumuellp/lights-camera-bum-action/ansible-test@v1
  with:
    playbooks-glob: "playbooks/*.yml tests/smoke-playbook.yml"
```

Or via the reusable workflow:

```yaml
jobs:
  ansible:
    uses: bumuellp/lights-camera-bum-action/.github/workflows/ansible-test.yml@v1
```
