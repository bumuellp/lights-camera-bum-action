# Pre-Commit Validation & Testing (`pre-commit`)

Run containerized pre-commit hooks, linters, formatters, and unit tests across all files using `ghcr.io/bumuellp/lint-tools`.

Eliminates developer toolchain drift by packaging `yamllint`, `shellcheck`, `shfmt`, `kubeconform`, `kube-score`, `kustomize`, `pre-commit`, `uv`, and Go inside a single zero-CVE container image.

## Usage

```yaml
- name: Run Pre-Commit & Tests
  uses: bumuellp/lights-camera-bum-action/pre-commit@v1
  with:
    extra-args: '--all-files'
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `extra-args` | Additional arguments to pass to `pre-commit run`. | No | `'--all-files'` |

## Shift-Left Integration
- In **pull requests and branch pushes**, this action executes the exact same tool versions used on local developer workstations via `cabumtain-hook`.
- If any linter fails or unit tests (`python-tests.sh` / `pytest`) fail, the action propagates the non-zero exit code, blocking the merge gate.
- Safely configures `git safe.directory "*"` and maps runner UID `$(id -u):$(id -g)` to prevent permission and file ownership issues.
