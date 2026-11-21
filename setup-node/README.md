# Setup Node.js Toolchain Action

Standardized GitHub Composite Action to set up Node.js with npm caching, optional Playwright browser installation, and configurable lint, typecheck, build, and test gates across one or more workspaces.

## Inputs

| Input | Description | Required | Default |
|---|---|---|---|
| `node-version` | Node.js version to set up (e.g. `20`, `24`) | No | `20` |
| `node-version-file` | Optional path to version file (e.g. `.nvmrc`) | No | `""` |
| `workspaces` | Space-separated package directories | No | `.` |
| `cache` | Enable npm and Playwright browser caching (`true`/`false`) | No | `true` |
| `cache-dependency-path` | Lockfile glob passed to `actions/setup-node` | No | `**/package-lock.json` |
| `install-deps` | Run `npm ci` (or `npm install` without lockfile) | No | `true` |
| `install-playwright` | Install Playwright browsers and OS deps | No | `false` |
| `playwright-browsers` | Space-separated Playwright browser targets | No | `chromium` |
| `run-lint` | Run `lint-script` across `workspaces` | No | `false` |
| `lint-script` | `package.json` script name for linting | No | `lint` |
| `run-typecheck` | Run `typecheck-script` across `workspaces` | No | `false` |
| `typecheck-script` | `package.json` script name for typechecking | No | `typecheck` |
| `run-build` | Run `build-script` across `workspaces` | No | `false` |
| `build-script` | `package.json` script name for building | No | `build` |
| `run-test` | Run `test-script` across `workspaces` | No | `false` |
| `test-script` | `package.json` script name for testing | No | `test` |

## Usage Example

```yaml
- name: Setup Node & Run Frontend Checks
  uses: bumuellp/lights-camera-bum-action/setup-node@main
  with:
    node-version: '20'
    workspaces: frontend
    run-lint: 'true'
    run-typecheck: 'true'
    run-build: 'true'
```
