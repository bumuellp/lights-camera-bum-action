# Plan Image Builds (`plan-image-builds`)

Smart build matrix planner for multi-container repositories. Discovers container configurations declaratively or dynamically from the file system, detects git path diffs to build only changed images on push, and supports selective UI dispatch (`all`, `auto`, or individual image checkboxes).

## Usage

```yaml
- name: Calculate Build Matrix
  id: plan
  uses: bumuellp/lights-camera-bum-action/plan-image-builds@v1
  with:
    images: 'auto' # or JSON array: '[{"name": "svc1", "path": "images/svc1"}]'
    target: 'auto' # or 'all', or image name
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `images` | JSON array of image configurations or `'auto'` for directory discovery under `images/`. | No | `auto` |
| `target` | Target image name to rebuild on dispatch, `'all'`, or `'auto'` to inspect commit diffs. | No | `auto` |

## Outputs

| Output | Description | Example |
| :--- | :--- | :--- |
| `matrix` | JSON string formatted for GitHub Actions `strategy.matrix` | `{"include": [{"name": "my-svc", "path": "images/my-svc", ...}]}` |
| `should-build` | Boolean string (`'true'` / `'false'`) indicating if any images need building | `'true'` |
