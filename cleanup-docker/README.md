# Cleanup Docker (`cleanup-docker`)

A teardown composite action designed for post-test steps in CI. It automatically displays container logs if a previous step failed (`if: failure()`) and tears down Docker containers and associated volumes (`docker compose down -v`) regardless of test outcome (`if: always()`).

## Usage

```yaml
- name: Teardown and Cleanup Docker
  if: always()
  uses: bumuellp/lights-camera-bum-action/cleanup-docker@v1
```

## Behavior & Steps

1. **`Show Docker logs on failure`** (`if: failure()`): Runs `docker compose logs` to output container logs directly into GitHub Actions console for rapid debugging of failed integration tests.
2. **`Cleanup Docker containers`** (`if: always()`): Runs `docker compose down -v` to ensure no orphan containers or dangling test volumes remain on the runner.
