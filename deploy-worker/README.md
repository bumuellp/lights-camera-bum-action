# Deploy Cloudflare Worker Action

Standardized GitHub Composite Action to build and deploy serverless Cloudflare Workers (JavaScript, TypeScript, or Rust compiled to WebAssembly) using Wrangler CLI with automated secret provisioning.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `api-token` | Cloudflare API token with `Workers:Edit` permission | **Yes** | — |
| `working-directory` | Directory containing `wrangler.toml` | No | `.` |
| `environment` | Optional Cloudflare environment (e.g. `production`) | No | `""` |
| `secrets` | Multiline list of secret names from `env` to provision | No | `""` |

## Usage Example

```yaml
- name: Deploy Worker
  uses: bumuellp/lights-camera-bum-action/deploy-worker@main
  with:
    api-token: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    working-directory: integrations/discord-bot
    secrets: |
      DISCORD_PUBLIC_KEY
      DISCORD_APPLICATION_ID
      GITHUB_PAT
  env:
    DISCORD_PUBLIC_KEY: ${{ secrets.DISCORD_PUBLIC_KEY }}
    DISCORD_APPLICATION_ID: ${{ secrets.DISCORD_APPLICATION_ID }}
    GITHUB_PAT: ${{ secrets.PAT_WATCHDOG }}
```
