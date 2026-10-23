# Parse Config YAML Action

Generic GitHub Composite Action to parse key-value pairs from YAML configuration files (with automatic fallback to `.example.yaml`) into a masked JSON object output.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `file` | Primary YAML configuration file to parse | No | `config/settings.yaml` |
| `fallback-file` | Fallback file if primary does not exist | No | `config/settings.example.yaml` |
| `keys` | Multiline or comma-separated list of keys | **Yes** | — |
| `mask` | Whether to call `::add-mask::` on values | No | `false` |

## Outputs

| Output | Description |
|---|---|
| `json` | Compact JSON string with requested key-value pairs |

## Usage Example

```yaml
- name: Parse Settings
  id: cfg
  uses: bumuellp/lights-camera-bum-action/parse-config@main
  with:
    file: config/settings.yaml
    fallback-file: config/settings.example.yaml
    keys: |
      domain
      server_type

- name: Display Configuration
  run: |
    echo "Domain: ${{ fromJSON(steps.cfg.outputs.json).domain }}"
```
