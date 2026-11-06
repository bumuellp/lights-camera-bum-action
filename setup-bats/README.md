# `setup-bats`

Composite GitHub Action to download, cache, and configure [bats-core (Bash Automated Testing System)](https://github.com/bats-core/bats-core) in GitHub Actions runner environments.

---

## 🚀 Features

* **Automated Caching**: Utilizes `actions/cache` keyed on runner OS and pinned version.
* **Pure Bash Installation**: Installs `bats-core` into `~/.local` and appends `~/.local/bin` to `$GITHUB_PATH`.
* **Idempotent**: Reuses an existing `bats` binary in PATH or `~/.local/bin` without re-downloading.

---

## 🛠 Usage

### Basic Usage
```yaml
- name: Setup Bats
  uses: bumuellp/lights-camera-bum-action/setup-bats@v1

- name: Run Shell Unit Tests
  run: bats tests/shell/
```

---

## 📋 Inputs

| Input | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| **`version`** | No | `v1.13.0` | Version of `bats-core` to install. |
| **`cache`** | No | `'true'` | Whether to enable `actions/cache` for the installation. |
