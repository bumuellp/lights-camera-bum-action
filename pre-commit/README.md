# Pre-Commit Validation & Testing (`pre-commit`)

Run pre-commit hooks, linters, formatters, and unit tests natively on the runner with automatic tool detection and `actions/cache@v6` caching (plus optional `lint-tools` container fallback).

## How Native Caching Works
1. **Inspect `.pre-commit-config.yaml`**: Only the tools actually referenced by your hooks (`shfmt`, `trufflehog`, `trivy`, `tofu`, `bats`, `hadolint`, `kubeconform`/`kube-score`/`kustomize`, `pytest`, `ansible-lint`) are installed in parallel.
2. **Cache Binaries, Hook Venvs & Trivy DB**: `~/.local/bin`, `~/.local/share/pre-commit-venv`, `~/.cache/pre-commit`, and `~/.cache/trivy` are cached across runs via `actions/cache@v6` — eliminating the multi-minute container image pull and cold hook setup.
3. **Optional Container Fallback**: Pass `use-container: 'true'` if a workflow explicitly requires `ghcr.io/bumuellp/lint-tools`.

## Usage

```yaml
- name: Run Pre-Commit & Tests
  uses: bumuellp/lights-camera-bum-action/pre-commit@v1
  with:
    extra-args: '--all-files --show-diff-on-failure'
```

## Key Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `extra-args` | Additional arguments to pass to `pre-commit run`. | No | `'--all-files'` |
| `cache` | Enable `actions/cache` for tools, hook venvs, and Trivy DB. | No | `'true'` |
| `use-container` | Run inside `lint-tools` container instead of natively. | No | `'false'` |
| `container-image` | Container image when `use-container: 'true'`. | No | `ghcr.io/bumuellp/lint-tools:v1.4.1@...` |
| `*-version` | Pinned versions (`pre-commit`, `yamllint`, `shfmt`, `trufflehog`, `trivy`, `tofu`, `hadolint`, `kubeconform`, `kubescore`, `kustomize`, `bats`) tracked by Renovate. | No | *(pinned defaults)* |
