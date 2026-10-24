# `rotate-hcloud-snapshots`

Lightweight composite GitHub Action to enforce snapshot retention policies in [Hetzner Cloud](https://docs.hetzner.cloud/).

Queries snapshots matching a given label selector, sorts them by creation date, retains the newest `keep` snapshot(s), and automatically deletes older ones to prevent obsolete storage accumulation.

---

## 🚀 Inputs

| Input | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| **`token`** | **Yes** | — | Hetzner Cloud API authentication token. |
| **`label-selector`** | **Yes** | — | Label selector query to filter snapshots (e.g. `role=golden-image` or `app=worker`). |
| **`keep`** | No | `1` | Number of recent snapshots to retain. |

---

## 📖 Usage Examples

### 1. Retain Single Golden Machine Image Snapshot
```yaml
- name: Rotate Old Snapshots
  uses: bumuellp/lights-camera-bum-action/rotate-hcloud-snapshots@v1
  with:
    token: ${{ secrets.HCLOUD_TOKEN }}
    label-selector: 'role=golden-image'
    keep: 1
```

### 2. Retain 3 Most Recent Backup Snapshots
```yaml
- name: Rotate Backup Snapshots
  uses: bumuellp/lights-camera-bum-action/rotate-hcloud-snapshots@v1
  with:
    token: ${{ secrets.HCLOUD_TOKEN }}
    label-selector: 'backup=nightly'
    keep: 3
```
