# Build and Push GHCR Image (`build-ghcr-image`)

Set up Docker Buildx, authenticate to GitHub Container Registry (GHCR), compute semantic version tag hierarchies, and build/push multi-architecture images with GitHub Actions caching (`type=gha`).

## Usage

```yaml
- name: Build and Push Container Image
  uses: bumuellp/lights-camera-bum-action/build-ghcr-image@v1
  with:
    context: ./images/my-service
    dockerfile: ./images/my-service/Dockerfile
    image-name: my-service
    repository-owner: ${{ github.repository_owner }}
    sha: ${{ github.sha }}
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
    extra-tags: v1.0.1
    push: true
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `context` | Docker build context directory. | **Yes** | — |
| `dockerfile` | Path to Dockerfile. | **Yes** | — |
| `image-name` | Image name under GHCR namespace. | **Yes** | — |
| `repository-owner` | GitHub repo/org owner used in image tag. | **Yes** | — |
| `sha` | Commit SHA tag. | **Yes** | — |
| `username` | Registry username. | **Yes** | — |
| `password` | Registry password or token. | **Yes** | — |
| `extra-tags` | Additional tags (e.g. `v1.0.1`, `v1`, `latest`). | No | `''` |
| `push` | Whether to push the image to GHCR. | No | `'true'` |
| `load` | Whether to load image into local Docker daemon. | No | `'false'` |
| `registry` | Container registry host. | No | `ghcr.io` |

## Tag Expansion Behavior
The internal `compute_tags.sh` helper expands semantic version release tags into canonical hierarchies:
- Release `v1.2.3` automatically generates:
  - `ghcr.io/<owner>/<name>:v1.2.3`
  - `ghcr.io/<owner>/<name>:v1.2`
  - `ghcr.io/<owner>/<name>:v1`
  - `ghcr.io/<owner>/<name>:latest`
  - `ghcr.io/<owner>/<name>:<sha>`
- Non-release branches tag `<sha>` and `<branch-slug>`.
