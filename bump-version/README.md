# Bump Version (`bump-version`)

Automated Semantic Version calculator based on **Conventional Commits** since the last git release tag.

## Usage

```yaml
- name: Calculate Next Version
  id: bump
  uses: bumuellp/lights-camera-bum-action/bump-version@v1
  with:
    force-bump: auto # Options: auto, patch, minor, major

- name: Display Computed Version
  run: |
    echo "Next Release: ${{ steps.bump.outputs.next-version }}"
    echo "Floating Major: ${{ steps.bump.outputs.major-version }}"
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `force-bump` | Force bump level (`'auto'`, `'patch'`, `'minor'`, `'major'`). | No | `auto` |

## Outputs

| Output | Description | Example |
| :--- | :--- | :--- |
| `next-version` | Full SemVer release tag | `v1.2.3` |
| `major-version` | Floating major version tag | `v1` |
| `minor-version` | Floating minor version tag | `v1.2` |
| `bump-type` | Type of bump calculated from git logs | `patch`, `minor`, `major`, or `none` |
| `previous-version` | Highest previous release tag found | `v1.2.2` |
| `has-changes` | Whether unreleased commits exist | `'true'` or `'false'` |

## Conventional Commits Logic
- **`feat!:`** or `BREAKING CHANGE:` $\rightarrow$ **Major** increment (`v1.2.3` $\rightarrow$ `v2.0.0`)
- **`feat:`** $\rightarrow$ **Minor** increment (`v1.2.3` $\rightarrow$ `v1.3.0`)
- **`fix:`, `perf:`, `refactor:`, `chore:`, `docs:`, `ci:`** $\rightarrow$ **Patch** increment (`v1.2.3` $\rightarrow$ `v1.2.4`)
