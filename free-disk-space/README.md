# Free Disk Space (`free-disk-space`)

Frees up 20GB+ of disk space on GitHub-hosted Ubuntu runners by removing pre-installed toolchains that are rarely needed in container and homelab CI pipelines (.NET, Android SDK, GHC, CodeQL caches).

## Usage

```yaml
- name: Reclaim Disk Space
  uses: bumuellp/lights-camera-bum-action/free-disk-space@v1
```

## Reclaimed Toolchains
- `/usr/share/dotnet`
- `/usr/local/lib/android`
- `/opt/ghc`
- `/opt/hostedtoolcache/CodeQL`

The action logs filesystem disk usage (`df -h`) before and after cleanup, and runs `rm -rf` safely and idempotently.
