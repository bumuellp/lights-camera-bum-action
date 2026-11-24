# `resolve-hcloud-placement`

Lightweight composite GitHub Action to evaluate and resolve the optimal available server type and datacenter location in [Hetzner Cloud](https://docs.hetzner.cloud/) using prioritized waterfall matching.

Queries Hetzner's server types catalog in a single API call and matches candidates across specified server types and locations, solving capacity shortages automatically.

---

## 🚀 Inputs

| Input | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| **`token`** | **Yes** | — | Hetzner Cloud API authentication token. |
| **`server-types`** | **Yes** | — | Candidate model or comma-/newline-separated waterfall list (e.g. `'cax21, cax31, cpx32'`). |
| **`locations`** | No | `'fsn1'` | Candidate location or comma-/newline-separated waterfall list (e.g. `'fsn1, nbg1, hel1'`). |
| **`strategy`** | No | `'type-first'` | Search strategy: `'type-first'` (prioritize server types across locations), `'location-first'` (prioritize datacenter locations across types), or `'type-price-first'` (preserve server type priority and pick the cheapest available location, breaking ties by `locations` order). |
| **`fail-on-unavailable`** | No | `'true'` | When `'true'`, fails the action if no candidate is available; when `'false'`, defaults to the first candidate with `available=false`. |

---

## 📤 Outputs

| Output | Description |
| :--- | :--- |
| **`server-type`** | Resolved available server type (e.g. `cax21`, `cpx32`). |
| **`location`** | Resolved available datacenter location (e.g. `fsn1`, `nbg1`). |
| **`architecture`** | CPU architecture of the resolved model (`arm` or `x86`). |
| **`cores`** | Number of vCPU cores of the resolved model. |
| **`memory`** | RAM in GB of the resolved model. |
| **`price-hourly`** | Hourly net price in EUR of the resolved model and location (empty if unavailable). |
| **`available`** | Boolean string indicating whether an available placement was found (`'true'` or `'false'`). |

---

## 📖 Usage Examples

### 1. Dynamic Datacenter Selection for Packer Builders (Location Waterfall)
When baking global snapshots, location does not matter. If `fsn1` is out of stock, automatically spin up in `nbg1` or `hel1`:

```yaml
- name: Resolve Builder Datacenter
  id: placement
  uses: bumuellp/lights-camera-bum-action/resolve-hcloud-placement@v1
  with:
    token: ${{ secrets.HCLOUD_TOKEN }}
    server-types: 'cax11'
    locations: 'fsn1, nbg1, hel1'

- name: Build Machine Image
  env:
    PKR_VAR_location: ${{ steps.placement.outputs.location }}
```

### 2. Sizing Waterfall for Location-Locked Servers (Server-Type Waterfall)
When storage volumes are locked to a specific datacenter (`fsn1`), try cheapest models first before falling back to high-availability tiers:

```yaml
- name: Resolve Server Model
  id: placement
  uses: bumuellp/lights-camera-bum-action/resolve-hcloud-placement@v1
  with:
    token: ${{ secrets.HCLOUD_TOKEN }}
    server-types: 'cax21, cax31, cpx32'
    locations: 'fsn1'
    strategy: 'type-first'

- name: Provision Ephemeral Server
  env:
    TF_VAR_server_type: ${{ steps.placement.outputs.server-type }}
```

### 3. Cost-Optimized Multi-Region Placement (`type-price-first`)
Preserve server-type tier priority while automatically selecting the cheapest available datacenter for each model (using `locations` order as tie-breaker):

```yaml
- name: Resolve Cheapest Placement for Tier
  id: placement
  uses: bumuellp/lights-camera-bum-action/resolve-hcloud-placement@v1
  with:
    token: ${{ secrets.HCLOUD_TOKEN }}
    server-types: 'cax21, cpx32'
    locations: 'fsn1, nbg1, hel1'
    strategy: 'type-price-first'

- name: Show Resolved Rate
  run: echo "Selected ${{ steps.placement.outputs.server-type }} in ${{ steps.placement.outputs.location }} at €${{ steps.placement.outputs.price-hourly }}/h"
```
