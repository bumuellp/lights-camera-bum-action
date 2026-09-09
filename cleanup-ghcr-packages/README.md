# Cleanup GHCR Packages (`cleanup-ghcr-packages`)

Automated package retention and cleanup policy for GitHub Container Registry (GHCR). Automatically prunes stale, untagged, and intermediate commit SHA images while guaranteeing that all SemVer release tags are preserved indefinitely.

## Retention Policy Rules
1. **SemVer Releases (`v*.*.*`)**: **Never deleted.** Pinned releases (e.g. `v1.0.0`, `v1.0.1`) are permanently protected.
2. **Commit SHAs**: Retains the most recent `N` (default: 5) commit SHA image versions. Older SHAs are automatically deleted.
3. **Untagged / Orphaned Images**: Deleted after a configurable retention window (default: 7 days) to free storage.

## Usage

```yaml
- name: Clean Stale GHCR Images
  uses: bumuellp/lights-camera-bum-action/cleanup-ghcr-packages@v1
  with:
    package-names: auto # or comma-separated list: "my-svc,other-svc"
    keep-sha-count: 5
    untagged-retention-days: 7
    token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `package-names` | Comma-separated or JSON list of package names, or `'auto'` to discover packages. | No | `auto` |
| `repository-owner` | GitHub repo or organization owner. | No | `${{ github.repository_owner }}` |
| `token` | GitHub token with `packages: write` permission. | No | `${{ github.token }}` |
| `keep-sha-count` | Number of recent commit SHA versions to retain. | No | `'5'` |
| `untagged-retention-days` | Grace period (in days) before deleting unreferenced untagged versions. | No | `'7'` |
| `dry-run` | Run policy analysis without deleting package versions. | No | `'false'` |
