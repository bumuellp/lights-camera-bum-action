# Setup OpenTofu Backend (`setup-tofu-backend`)

Initializes OpenTofu projects with an S3-compatible remote state backend (e.g. Hetzner Object Storage, MinIO, Ceph, AWS S3) by injecting `-backend-config` parameters and automatically masking access credentials.

---

## 📋 Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `bucket` | Name of the S3 bucket storing state. | **Yes** | — |
| `endpoint` | S3 endpoint URL (e.g. `https://fsn1.your-objectstorage.com`). | **Yes** | — |
| `key` | State file key path within bucket. | No | `terraform.tfstate` |
| `region` | Region string required by S3 client. | No | `us-east-1` |
| `access-key` | S3 Access Key ID. | **Yes** | — |
| `secret-key` | S3 Secret Access Key. | **Yes** | — |
| `working-directory` | Path to directory containing OpenTofu files. | No | `.` |

---

## 🚀 Usage Example

```yaml
- name: Setup OpenTofu
  uses: opentofu/setup-opentofu@v1
  with:
    tofu_version_file: .tofu-version

- name: Initialize Backend
  uses: bumuellp/lights-camera-bum-action/setup-tofu-backend@v1
  with:
    working-directory: iac
    bucket: my-infra-state
    endpoint: https://fsn1.your-objectstorage.com
    key: minecraft/state.tfstate
    access-key: ${{ secrets.S3_ACCESS_KEY }}
    secret-key: ${{ secrets.S3_SECRET_KEY }}
```
