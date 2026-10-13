# Decrypt SOPS Secrets (`decrypt-sops`)

Decrypts SOPS-encrypted files using an Age secret key (`SOPS_AGE_KEY`), setting proper file permissions (`0600`) and gracefully handling missing files or keys. If `sops` is not already installed on the runner, it automatically downloads and configures the binary.

---

## 📋 Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `age-key` | Age secret key for decryption (`AGE-SECRET-KEY-1...`). | No | `""` |
| `file` | Path to the encrypted file. | No | `config/secrets.enc.yaml` |
| `output` | Output path for the decrypted file. | No | `config/secrets.yaml` |
| `mode` | File permissions mode for the decrypted file. | No | `0600` |
| `sops-version` | Fallback version of SOPS to install if missing. | No | `3.9.4` |

---

## 📤 Outputs

| Output | Description |
| :--- | :--- |
| `decrypted` | Boolean string (`true` or `false`) indicating if decryption succeeded. |

---

## 🚀 Usage Example

```yaml
- name: Decrypt Secrets
  uses: bumuellp/lights-camera-bum-action/decrypt-sops@v1
  with:
    age-key: ${{ secrets.SOPS_AGE_KEY }}
    file: config/secrets.enc.yaml
    output: config/secrets.yaml
```
