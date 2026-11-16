# Setup Rust Toolchain Action

Standardized GitHub Composite Action to set up the Rust toolchain, components, compilation targets, optional caching with Swatinem/rust-cache, and optional `worker-build` utility.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `toolchain` | Rust toolchain version (e.g. `stable`, `1.85.0`) | No | `stable` |
| `components` | Rustup components to install | No | `clippy, rustfmt` |
| `targets` | Compilation targets to install | No | `""` |
| `cache` | Enable Swatinem/rust-cache (`true`/`false`) | No | `true` |
| `workspaces` | Workspace paths for cache scoping | No | `""` |
| `install-worker-build` | Install Cloudflare `worker-build` | No | `false` |
| `run-fmt` | Run `cargo fmt --check` across `workspaces` | No | `false` |
| `run-clippy` | Run `cargo clippy` across `workspaces` | No | `false` |
| `clippy-args` | Arguments passed to `cargo clippy` | No | `--all-targets -- -D warnings` |
| `run-test` | Run `cargo test` across `workspaces` | No | `false` |
| `test-args` | Additional arguments passed to `cargo test` | No | `""` |

## Usage Example

```yaml
- name: Setup Rust
  uses: bumuellp/lights-camera-bum-action/setup-rust@main
  with:
    components: clippy, rustfmt
    workspaces: integrations/discord-bot
    install-worker-build: true
```
