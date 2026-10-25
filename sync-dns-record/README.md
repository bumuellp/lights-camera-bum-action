# `sync-dns-record`

Provider-agnostic composite GitHub Action for synchronizing and removing DNS records via REST APIs.

Supports **[deSEC.io](https://desec.io)**, **[IONOS Domain API](https://developer.hosting.ionos.de/docs/dns)**, and **[Hetzner DNS](https://docs.hetzner.cloud/reference/cloud#zones)** out of the box.

---

## 🚀 Inputs

| Input | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| **`provider`** | No | `desec` | DNS provider: `desec`, `ionos`, or `hetzner`. |
| **`token`** | **Yes** | — | API Token (deSEC Token, IONOS `X-API-Key`, or Hetzner Cloud API token). |
| **`domain`** | **Yes** | — | Registered zone / domain (e.g. `example.dedyn.io` or `example.com`). |
| **`subname`** | No | `""` | Subdomain label (e.g. `mc` or `@` / empty for apex root). |
| **`type`** | No | `A` | DNS record type (`A`, `AAAA`, `TXT`, `CNAME`). |
| **`records`** | Conditional | `""` | Target value(s) (required when `action: sync`). |
| **`ttl`** | No | `60` | Time To Live in seconds. |
| **`action`** | No | `sync` | Action to execute: `sync` (upsert) or `delete`. |

---

## 📖 Usage Examples

### 1. Synchronizing an A-Record on deSEC.io
```yaml
- name: Update deSEC DNS Record
  uses: bumuellp/lights-camera-bum-action/sync-dns-record@v1
  with:
    provider: desec
    token: ${{ secrets.DESEC_TOKEN }}
    domain: my-server.dedyn.io
    subname: mc
    type: A
    records: ${{ steps.tofu.outputs.server_ip }}
    ttl: 60
    action: sync
```

### 2. Synchronizing an A-Record on IONOS
```yaml
- name: Update IONOS DNS Record
  uses: bumuellp/lights-camera-bum-action/sync-dns-record@v1
  with:
    provider: ionos
    token: ${{ secrets.IONOS_API_KEY }} # format: prefix.secret
    domain: example.com
    subname: mc
    type: A
    records: ${{ steps.tofu.outputs.server_ip }}
    ttl: 300
    action: sync
```

### 3. Synchronizing an A-Record on Hetzner DNS
```yaml
- name: Update Hetzner DNS Record
  uses: bumuellp/lights-camera-bum-action/sync-dns-record@v1
  with:
    provider: hetzner
    token: ${{ secrets.HCLOUD_TOKEN }}
    domain: example.com
    subname: mc
    type: A
    records: ${{ steps.tofu.outputs.server_ip }}
    ttl: 60
    action: sync
```

### 4. Deleting a Record upon Teardown
```yaml
- name: Remove DNS Record
  uses: bumuellp/lights-camera-bum-action/sync-dns-record@v1
  if: always()
  with:
    provider: hetzner
    token: ${{ secrets.HCLOUD_TOKEN }}
    domain: example.com
    subname: mc
    type: A
    action: delete
```
