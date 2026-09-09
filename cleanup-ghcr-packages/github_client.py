"""GitHub Container Registry and Packages API Client using PyGithub."""

from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.request
from typing import Any

from github import Auth, Github, GithubException


class GitHubPackagesClient:
    """Client for querying and managing GHCR package versions and OCI manifests."""

    def __init__(
        self,
        token: str,
        owner: str = "",
        registry_url: str = "https://ghcr.io",
    ):
        self.token = token.strip()
        self.owner = owner.strip()
        self.registry_url = registry_url.rstrip("/")
        self._gh = Github(auth=Auth.Token(self.token)) if self.token else Github()
        self._is_org: bool | None = None
        self._ghcr_tokens: dict[str, str] = {}

    def _check_is_org(self) -> bool:
        """Determine whether the repository owner is an organization or a user."""
        if self._is_org is not None:
            return self._is_org
        if not self.owner:
            self._is_org = False
            return False

        try:
            org = self._gh.get_organization(self.owner)
            self._is_org = bool(org and org.login)
        except Exception:
            self._is_org = False
        return self._is_org

    def get_package_versions(self, package_name: str) -> list[dict[str, Any]]:
        """Fetch all package versions for a container package with pagination."""
        versions: list[dict[str, Any]] = []
        is_org = self._check_is_org()

        if is_org:
            base_endpoint = f"/orgs/{self.owner}/packages/container/{package_name}/versions"
        elif self.owner:
            base_endpoint = f"/users/{self.owner}/packages/container/{package_name}/versions"
        else:
            base_endpoint = f"/user/packages/container/{package_name}/versions"

        page = 1
        per_page = 100

        while True:
            url = f"{base_endpoint}?per_page={per_page}&page={page}"
            try:
                headers, data = self._gh.requester.requestJsonAndCheck("GET", url)
                if not data or not isinstance(data, list):
                    break
                versions.extend(data)
                if len(data) < per_page:
                    break
                page += 1
            except GithubException as e:
                # If /users/{owner} returns 404, fall back to authenticated /user endpoint
                if e.status == 404 and self.owner and not is_org:
                    fallback_url = f"/user/packages/container/{package_name}/versions?per_page={per_page}&page={page}"
                    try:
                        headers, data = self._gh.requester.requestJsonAndCheck("GET", fallback_url)
                        if not data or not isinstance(data, list):
                            break
                        versions.extend(data)
                        if len(data) < per_page:
                            break
                        page += 1
                        continue
                    except Exception as fallback_e:
                        print(
                            f"[{package_name}] Warning: Failed to fetch versions via fallback: {fallback_e}",
                            file=sys.stderr,
                        )
                        break
                print(
                    f"[{package_name}] Warning: Failed to fetch versions (HTTP {e.status}): {e.data}",
                    file=sys.stderr,
                )
                break
            except Exception as e:
                print(f"[{package_name}] Error fetching versions: {e}", file=sys.stderr)
                break

        return versions

    def _get_registry_token(self, owner: str, package_name: str) -> str:
        """Acquire a token for querying the GHCR OCI registry."""
        cache_key = f"{owner}/{package_name}"
        if cache_key in self._ghcr_tokens:
            return self._ghcr_tokens[cache_key]

        token_url = f"{self.registry_url}/token?scope=repository:{owner}/{package_name}:pull"
        headers = {"User-Agent": "lights-camera-bum-action/cleanup-ghcr-packages"}
        if self.token:
            auth_bytes = f"{self.owner or 'token'}:{self.token}".encode()
            headers["Authorization"] = f"Basic {base64.b64encode(auth_bytes).decode('utf-8')}"

        req = urllib.request.Request(token_url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                tok = data.get("token", "")
                self._ghcr_tokens[cache_key] = tok
                return tok
        except Exception:
            return self.token

    def get_index_child_digests(self, package_name: str, reference: str) -> set[str]:
        """Query GHCR OCI registry to extract child manifest digests if reference is an OCI Index."""
        owner = self.owner
        if not owner:
            return set()

        reg_token = self._get_registry_token(owner, package_name)
        headers = {
            "Accept": (
                "application/vnd.oci.image.index.v1+json, "
                "application/vnd.docker.distribution.manifest.list.v2+json, "
                "application/vnd.oci.image.manifest.v1+json, "
                "application/vnd.docker.distribution.manifest.v2+json"
            ),
            "User-Agent": "lights-camera-bum-action/cleanup-ghcr-packages",
        }
        if reg_token:
            headers["Authorization"] = f"Bearer {reg_token}"

        manifest_url = f"{self.registry_url}/v2/{owner}/{package_name}/manifests/{reference}"
        req = urllib.request.Request(manifest_url, headers=headers)

        child_digests: set[str] = set()
        try:
            with urllib.request.urlopen(req) as resp:
                manifest_data = json.loads(resp.read().decode("utf-8"))
                manifests = manifest_data.get("manifests", [])
                for m in manifests:
                    digest = m.get("digest")
                    if digest:
                        child_digests.add(digest)
        except Exception:
            pass

        return child_digests

    def delete_package_version(self, package_name: str, version_id: int) -> bool:
        """Delete a package version by its ID."""
        is_org = self._check_is_org()
        if is_org:
            endpoint = f"/orgs/{self.owner}/packages/container/{package_name}/versions/{version_id}"
        else:
            endpoint = f"/user/packages/container/{package_name}/versions/{version_id}"

        try:
            self._gh.requester.requestJsonAndCheck("DELETE", endpoint)
            return True
        except GithubException as e:
            print(f"    -> Delete failed (HTTP {e.status}): {e.data}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"    -> Delete error: {e}", file=sys.stderr)
            return False
