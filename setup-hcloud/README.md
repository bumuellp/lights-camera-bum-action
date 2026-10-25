# `setup-hcloud`

Composite GitHub Action to download, cache, and configure the official [Hetzner Cloud CLI (`hcloud`)](https://github.com/hetznercloud/cli) in GitHub Actions runner environments.

---

## 🚀 Features

* **Automated Caching**: Utilizes `actions/cache` keyed on OS, architecture, and pinned version.
* **Multi-Architecture**: Automatically detects `x86_64` (amd64) and `aarch64` / `arm64`.
* **Credential Masking**: Automatically masks API tokens using `::add-mask::` and exports `HCLOUD_TOKEN` into `$GITHUB_ENV`.
* **Idempotent**: Reuses an existing `hcloud` binary in PATH or `~/.local/bin` without re-downloading.

---

## 🛠 Usage

### Basic Usage
```yaml
- name: Setup Hetzner Cloud CLI
  uses: bumuellp/lights-camera-bum-action/setup-hcloud@v1
  with:
    token: ${{ secrets.HCLOUD_TOKEN }}

- name: List Hetzner Servers
  run: hcloud server list
```

### Custom Version & Disabling Cache
```yaml
- name: Setup Specific hcloud Version
  uses: bumuellp/lights-camera-bum-action/setup-hcloud@v1
  with:
    version: 'v1.70.2'
    cache: 'false'
```

---

## 📋 Inputs

| Input | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| **`version`** | No | `v1.70.2` | Version of `hcloud` to install. |
| **`token`** | No | `""` | Hetzner Cloud API token to mask and export to `$GITHUB_ENV`. |
| **`cache`** | No | `'true'` | Whether to enable `actions/cache` for the binary. |
