# `tofu-module-test`

Composite GitHub Action to set up OpenTofu, cache provider plugins (`TF_PLUGIN_CACHE_DIR`), run `tofu init -backend=false` + `tofu validate`, and execute `tofu test` across matching OpenTofu module directories when `*.tftest.hcl` or `*.tftest.json` files exist.

## Inputs

| Input | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `modules-glob` | No | `modules/*` | Space-separated glob pattern(s) of OpenTofu module directories. |
| `tofu-version` | No | `""` | Explicit OpenTofu version (overrides `tofu-version-file`). |
| `tofu-version-file` | No | `.tofu-version` | File containing the OpenTofu version. |
| `cache` | No | `'true'` | Cache provider plugins via `actions/cache` (`'true'`/`'false'`). |
| `run-tests` | No | `'true'` | Run `tofu test` when `.tftest.hcl` or `.tftest.json` files exist. |

## Usage

```yaml
- uses: bumuellp/lights-camera-bum-action/tofu-module-test@v1
  with:
    modules-glob: "modules/*"
```
