"""Publish Helm OCI artifacts using Docker credentials and the registry HTTP API."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

import httpx

from .common import Error
from .registry import HELM_CONFIG, HELM_LAYER, PUBLICATION, wait_for_manifest

MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"


def docker_credentials(host):
    """Read only this registry's Docker credentials; never log helper output."""
    directory = Path(os.environ.get("DOCKER_CONFIG", Path.home() / ".docker"))
    config_path = directory / "config.json"
    if not config_path.exists():
        return None
    try:
        config = json.loads(config_path.read_text())
        helper = config.get("credHelpers", {}).get(host) or config.get("credsStore")
        if helper:
            if not re.fullmatch(r"[a-zA-Z0-9_.-]+", helper):
                raise ValueError("invalid helper name")
            result = subprocess.run(
                ["docker-credential-" + helper, "get"],
                input=host + "\n",
                text=True,
                capture_output=True,
            )
            if result.returncode:
                if "credentials not found" in (result.stdout + result.stderr).lower():
                    return None
                raise ValueError("credential helper failed")
            saved = json.loads(result.stdout)
            username, secret = saved["Username"], saved["Secret"]
        else:
            saved = config.get("auths", {}).get(host, {})
            if not saved.get("auth"):
                return None
            username, secret = (
                base64.b64decode(saved["auth"], validate=True).decode().split(":", 1)
            )
        if not username or not secret or username == "<token>":
            raise ValueError("username/password credentials are required")
        return username, secret
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Error(
            f"Cannot read Docker credentials; run docker login {host}"
        ) from error


class ChartRegistry:
    """Read, upload and retag Helm manifests in one OCI repository without ORAS."""

    def __init__(self, repository, *, plain_http=False, client=None, credentials=None):
        self.repository = repository
        host, self.name = repository.split("/", 1)
        self.base = httpx.URL(
            f'{"http" if plain_http else "https"}://{host}/v2/{self.name}/'
        )
        if plain_http and self.base.host not in ("localhost", "127.0.0.1", "::1"):
            raise Error("Plain HTTP is allowed only for disposable loopback registries")
        self.host = host
        self.client = (
            client
            if client is not None
            else httpx.Client(timeout=60, follow_redirects=False)
        )
        self.credentials = credentials or docker_credentials
        self.token = None
        self._digests = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def _same_origin(self, url):
        return (url.scheme, url.host, url.port) == (
            self.base.scheme,
            self.base.host,
            self.base.port,
        )

    def _authorize(self, challenge):
        if not challenge.lower().startswith("bearer "):
            raise Error(f"Registry authentication failed; run docker login {self.host}")
        fields = dict(re.findall(r'(\w+)="([^"]*)"', challenge))
        realm = httpx.URL(fields.get("realm", ""))
        if not self._same_origin(realm):
            raise Error(
                "Refusing to send Docker credentials to another registry origin"
            )
        response = self.client.get(
            realm,
            params={
                "service": fields.get("service", self.host),
                "scope": f"repository:{self.name}:pull,push",
            },
            auth=self.credentials(self.host),
            follow_redirects=False,
        )
        if response.status_code != 200:
            raise Error(
                f"Registry authentication failed ({response.status_code}); run docker login {self.host}"
            )
        data = response.json()
        self.token = data.get("token") or data.get("access_token")
        if not isinstance(self.token, str) or not self.token:
            raise Error("Registry did not return an access token")

    def _request(self, method, url, *, expected=(200,), **kwargs):
        url = httpx.URL(url)
        if not self._same_origin(url):
            raise Error("Refusing a registry upload/redirect to another origin")
        headers = kwargs.pop("headers", {})
        try:
            for attempt in range(2):
                authorization = (
                    {"Authorization": "Bearer " + self.token} if self.token else {}
                )
                response = self.client.request(
                    method,
                    url,
                    headers=headers | authorization,
                    follow_redirects=False,
                    **kwargs,
                )
                if response.status_code != 401 or attempt:
                    break
                self._authorize(response.headers.get("WWW-Authenticate", ""))
            if response.status_code not in expected:
                raise Error(
                    f"Registry {method} failed for {self.repository} ({response.status_code}); check docker login {self.host} and package permissions"
                )
            return response
        except httpx.HTTPError as error:
            raise Error(
                f"Registry {method} request failed for {self.repository}"
            ) from error

    def _manifest_url(self, ref):
        repository, separator, version = ref.rpartition("@")
        if not separator:
            repository, _, version = ref.rpartition(":")
        if repository != self.repository or not version:
            raise Error("Chart reference must belong to the configured repository")
        return self.base.join("manifests/" + quote(version, safe=":"))

    def manifest(self, ref):
        """Return None only on HTTP 404; cache the digest of the exact response bytes."""
        self._digests.pop(ref, None)
        response = self._request(
            "GET",
            self._manifest_url(ref),
            expected=(200, 404),
            headers={"Accept": MANIFEST_TYPE},
        )
        if response.status_code == 404:
            return None
        manifest = response.json()
        if not isinstance(manifest, dict) or manifest.get("mediaType") != MANIFEST_TYPE:
            raise Error(f"Invalid Helm OCI manifest: {ref}")
        self._digests[ref] = "sha256:" + hashlib.sha256(response.content).hexdigest()
        return manifest

    def digest(self, ref):
        if ref not in self._digests and self.manifest(ref) is None:
            raise Error(f"Chart manifest is missing: {ref}")
        return self._digests[ref]

    def _blob(self, path, media_type):
        content = path.read_bytes()
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        response = self._request(
            "POST", self.base.join("blobs/uploads/"), expected=(202,)
        )
        location = response.headers.get("Location")
        if not location:
            raise Error("Registry did not provide a blob upload location")
        upload = response.url.join(location).copy_add_param("digest", digest)
        self._request(
            "PUT",
            upload,
            expected=(201,),
            content=content,
            headers={"Content-Type": "application/octet-stream"},
        )
        return {"mediaType": media_type, "digest": digest, "size": len(content)}

    def push_chart(self, repository, archive, config, publication):
        """Publish the standard Helm config and one chart layer at the version tag."""
        if repository != self.repository:
            raise Error("Chart repository mismatch")
        manifest = {
            "schemaVersion": 2,
            "mediaType": MANIFEST_TYPE,
            "config": self._blob(config, HELM_CONFIG),
            "layers": [self._blob(archive, HELM_LAYER)],
            "annotations": {
                PUBLICATION: json.dumps(publication, sort_keys=True),
                "org.opencontainers.image.source": "https://github.com/"
                + self.name.removesuffix("/helm"),
                "org.opencontainers.image.revision": publication["source_sha"],
                "org.opencontainers.image.version": publication["chart_version"],
            },
        }
        content = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        ref = repository + ":" + publication["chart_version"]
        self._request(
            "PUT",
            self._manifest_url(ref),
            expected=(201,),
            content=content,
            headers={"Content-Type": MANIFEST_TYPE},
        )
        wait_for_manifest(self, ref, digest=digest)
        return digest

    def alias(self, repository, digest, tag):
        """Copy the existing manifest bytes so the channel preserves its digest."""
        source = repository + "@" + digest
        response = self._request(
            "GET", self._manifest_url(source), headers={"Accept": MANIFEST_TYPE}
        )
        if "sha256:" + hashlib.sha256(response.content).hexdigest() != digest:
            raise Error("Registry returned a different chart digest")
        self._request(
            "PUT",
            self._manifest_url(repository + ":" + tag),
            expected=(201,),
            content=response.content,
            headers={"Content-Type": MANIFEST_TYPE},
        )
