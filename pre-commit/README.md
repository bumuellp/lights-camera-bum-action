# Pre-Commit Validation & Testing (`pre-commit`)

Run pre-commit hooks natively on the runner with **generic, hook-driven tool discovery** (`mise` + `pre-commit`) and `actions/cache@v6` caching — zero hardcoded hook names or tool versions in this action.

## How Generic Tool Discovery Works

1. **`pre-commit install-hooks`** clones external hook repositories at their exact pinned `rev:` and caches `~/.cache/pre-commit`.
2. **`discover_tools.py`** collects `mise` tool specifications generically from:
   * A companion **`.pre-commit-tools.yaml`** (or `.yml`) inside any referenced hook repository (mapping enabled hook IDs or `_default` to `mise` specs, e.g. `trivy@0.75.0`, `shfmt@3.14.1`, `pipx:yamllint@1.37.1`).
   * Optional **`[tools: ...]`** or **`[requires: ...]`** annotations inside a hook's `description:` field in `.pre-commit-hooks.yaml` or `.pre-commit-config.yaml` (`local` hooks).
   * Project-level **`mise.toml` / `.mise.toml` / `.tool-versions`**.
   * Optional **`tools`** input passed to this action.
3. **`mise`** installs and caches all discovered tools under `~/.local/share/mise` before executing `pre-commit run`.

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
| `tools` | Optional extra `mise` tool specs (e.g. `trivy@0.75.0`). | No | `''` |
| `cache` | Enable `actions/cache@v6` for venv, hooks, mise tools, and Trivy DB. | No | `'true'` |
| `pre-commit-version` | Pinned `pre-commit` version (tracked by Renovate). | No | `'4.6.2'` |
| `use-container` | Run inside `lint-tools` container instead of natively. | No | `'false'` |
| `container-image` | Container image used when `use-container: 'true'`. | No | `ghcr.io/bumuellp/lint-tools:v1.4.1@...` |
