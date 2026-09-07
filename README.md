# lights-camera-bum-action

Reusable GitHub Actions suite for CI pipelines, linting, Docker image building, and deployment workflows across homelab and application repositories.

---

## 🎬 Action Catalog

### 1. `lint` (`bumuellp/lights-camera-bum-action/lint@main`)
Runs `pre-commit` hooks inside a tool container.

#### Usage:
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: bumuellp/lights-camera-bum-action/lint@main
```

---

### 2. `build-ghcr-image` (`bumuellp/lights-camera-bum-action/build-ghcr-image@main`)
Builds and pushes a container image to GitHub Container Registry (GHCR) using Buildx and GitHub Actions cache.

#### Usage:
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: bumuellp/lights-camera-bum-action/build-ghcr-image@main
    with:
      context: images/lint-tools
      dockerfile: images/lint-tools/Dockerfile
      image-name: lint-tools
      repository-owner: ${{ github.repository_owner }}
      sha: ${{ github.sha }}
      username: ${{ github.actor }}
      password: ${{ secrets.GITHUB_TOKEN }}
```
