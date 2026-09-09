# lights-camera-bum-action

Reusable, production-grade GitHub Actions suite for CI/CD pipelines, container packaging, automated SemVer bumping, package retention, and secure deployments across homelab and application repositories.

---

## 🎬 Action Catalog

| Action | Description | Documentation |
| :--- | :--- | :--- |
| **[`pre-commit`](pre-commit/)** | Run containerized pre-commit linters and tests via `ghcr.io/bumuellp/lint-tools`. | [Read Docs](pre-commit/README.md) |
| **[`build-ghcr-image`](build-ghcr-image/)** | Buildx container image builder with GHA caching and dynamic SemVer tag expansion. | [Read Docs](build-ghcr-image/README.md) |
| **[`bump-version`](bump-version/)** | Automated SemVer release calculator based on Conventional Commits. | [Read Docs](bump-version/README.md) |
| **[`cleanup-ghcr-packages`](cleanup-ghcr-packages/)** | Automated GHCR image retention policy preserving releases and pruning stale SHAs. | [Read Docs](cleanup-ghcr-packages/README.md) |
| **[`plan-image-builds`](plan-image-builds/)** | Smart build matrix planner with git path diffs and workflow dispatch support. | [Read Docs](plan-image-builds/README.md) |
| **[`free-disk-space`](free-disk-space/)** | Frees 20GB+ disk space on Ubuntu runners by safely removing unused SDKs. | [Read Docs](free-disk-space/README.md) |
| **[`cleanup-docker`](cleanup-docker/)** | Post-test teardown displaying compose logs on failure and stopping containers. | [Read Docs](cleanup-docker/README.md) |
| **[`run-authorized-ssh-script`](run-authorized-ssh-script/)** | Execute deployment scripts on remote hosts over SSH with piped environment payloads. | [Read Docs](run-authorized-ssh-script/README.md) |
| **[`sync-rsync-path`](sync-rsync-path/)** | Synchronize local files and artifacts to remote hosts over SSH using `rsync`. | [Read Docs](sync-rsync-path/README.md) |

---

## 🚀 Quick Usage Examples

### 1. Continuous Integration & Pre-Commit (`pre-commit`)
```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Run Linters & Tests
        uses: bumuellp/lights-camera-bum-action/pre-commit@v1
```

### 2. Automatic SemVer Calculation (`bump-version`)
```yaml
jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - id: bump
        uses: bumuellp/lights-camera-bum-action/bump-version@v1
      - run: echo "Next Version: ${{ steps.bump.outputs.next-version }}"
```

### 3. Building & Pushing to GHCR (`build-ghcr-image`)
```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: bumuellp/lights-camera-bum-action/build-ghcr-image@v1
        with:
          context: ./images/my-service
          dockerfile: ./images/my-service/Dockerfile
          image-name: my-service
          repository-owner: ${{ github.repository_owner }}
          sha: ${{ github.sha }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
          extra-tags: ${{ steps.bump.outputs.next-version }}
```

---

## 🧪 Testing Pyramid & Quality Assurance

This repository employs a 3-tier testing architecture:
1. **Static Analysis & Schema Validation**:
   - `pre-commit` enforces `yamllint`, `shellcheck`, and `check-jsonschema` (verifying action and workflow manifests against official GitHub Action schemas).
2. **Unit & Behavioral Testing**:
   - 40 unit tests in `tests/` executed via `pytest`, testing Python helpers, bash execution scripts, exit code propagation, whitespace handling, and error conditions.
3. **Integration Testing (`act`)**:
   - `.github/workflows/integration-tests.yml` exercises every composite action with positive and negative test cases.
   - Runnable in CI on PRs, or locally via `act -W .github/workflows/integration-tests.yml`.
