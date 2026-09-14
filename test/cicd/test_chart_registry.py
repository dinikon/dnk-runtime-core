"""Helm OCI upload protocol, Docker authentication and channel digest preservation."""

import base64
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import httpx

from scripts.cicd.chart_registry import ChartRegistry, MANIFEST_TYPE, docker_credentials
from scripts.cicd.common import Error
from scripts.cicd.registry import HELM_CONFIG, HELM_LAYER, PUBLICATION


class RegistryServer:
    """In-memory implementation of the OCI endpoints used by the chart publisher."""

    def __init__(self):
        self.manifests = {}
        self.blobs = {}
        self.requests = []
        self.realm = "https://ghcr.io/token"
        self.location = "/v2/example/project/helm/blobs/uploads/1?_state=opaque"
        self.denied = False
        self.fail_upload = False

    def __call__(self, request):
        self.requests.append(request)
        path = request.url.path
        if path == "/token":
            return httpx.Response(200, json={"token": "registry-secret-token"})
        if self.denied:
            return httpx.Response(403)
        if request.headers.get("Authorization") != "Bearer registry-secret-token":
            return httpx.Response(
                401,
                headers={
                    "WWW-Authenticate": f'Bearer realm="{self.realm}",service="ghcr.io"'
                },
            )
        if request.method == "POST" and path.endswith("/blobs/uploads/"):
            return httpx.Response(202, headers={"Location": self.location})
        if request.method == "PUT" and "/blobs/uploads/" in path:
            if self.fail_upload:
                return httpx.Response(500)
            digest = request.url.params["digest"]
            assert request.url.params["_state"] == "opaque"
            assert digest == "sha256:" + hashlib.sha256(request.content).hexdigest()
            self.blobs[digest] = request.content
            return httpx.Response(201)
        if "/manifests/" in path:
            ref = path.split("/manifests/", 1)[1]
            if request.method == "PUT":
                manifest = json.loads(request.content)
                for blob in [manifest["config"], *manifest["layers"]]:
                    assert blob["digest"] in self.blobs
                    assert blob["size"] == len(self.blobs[blob["digest"]])
                digest = "sha256:" + hashlib.sha256(request.content).hexdigest()
                self.manifests[ref] = self.manifests[digest] = request.content
                return httpx.Response(201)
            if ref in self.manifests:
                return httpx.Response(
                    200,
                    content=self.manifests[ref],
                    headers={"Content-Type": MANIFEST_TYPE},
                )
            return httpx.Response(404)
        raise AssertionError(f"Unexpected request: {request.method} {path}")


class ChartRegistryTests(unittest.TestCase):
    repository = "ghcr.io/example/project/helm"

    def setUp(self):
        self.server = RegistryServer()
        self.credentials = Mock(return_value=("developer", "docker-login-secret"))
        self.registry = self.enterContext(
            ChartRegistry(
                self.repository,
                client=httpx.Client(transport=httpx.MockTransport(self.server)),
                credentials=self.credentials,
            )
        )
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.archive = self.directory / "chart.tgz"
        self.archive.write_bytes(b"test chart archive bytes")
        self.config = self.directory / "config.json"
        self.config.write_text('{"name":"project","version":"0.3.2-feat.g12345678"}')
        self.record = {"chart_version": "0.3.2-feat.g12345678", "source_sha": "a" * 40}

    def publish(self):
        return self.registry.push_chart(
            self.repository, self.archive, self.config, self.record
        )

    def test_pushes_helm_media_types_then_aliases_the_exact_digest(self):
        ref = self.repository + ":" + self.record["chart_version"]
        self.assertIsNone(self.registry.manifest(ref))
        digest = self.publish()
        manifest = self.registry.manifest(ref)
        self.assertEqual(manifest["config"]["mediaType"], HELM_CONFIG)
        self.assertEqual(
            [layer["mediaType"] for layer in manifest["layers"]], [HELM_LAYER]
        )
        self.assertEqual(json.loads(manifest["annotations"][PUBLICATION]), self.record)
        self.registry.alias(self.repository, digest, "feat")
        self.assertEqual(self.registry.manifest(self.repository + ":feat"), manifest)
        self.assertEqual(self.registry.digest(self.repository + ":feat"), digest)
        self.assertEqual(
            self.server.manifests["feat"],
            self.server.manifests[self.record["chart_version"]],
        )
        tokens = [r for r in self.server.requests if r.url.path == "/token"]
        self.assertEqual(len(tokens), 1)
        self.assertEqual(
            tokens[0].url.params["scope"], "repository:example/project/helm:pull,push"
        )
        self.assertEqual(
            tokens[0].headers["Authorization"],
            "Basic " + base64.b64encode(b"developer:docker-login-secret").decode(),
        )
        self.credentials.assert_called_once_with("ghcr.io")

    def test_missing_chart_does_not_resolve_a_digest(self):
        ref = self.repository + ":absent"
        self.assertIsNone(self.registry.manifest(ref))
        with self.assertRaisesRegex(Error, "Chart manifest is missing"):
            self.registry.digest(ref)

    def test_access_failure_is_not_a_missing_chart(self):
        self.server.denied = True
        with self.assertRaisesRegex(Error, "403"):
            self.registry.manifest(self.repository + ":absent")
        self.assertEqual(self.server.blobs, {})
        self.assertEqual(self.server.manifests, {})

    def test_credentials_cannot_be_sent_to_a_foreign_token_endpoint(self):
        self.server.realm = "https://example.invalid/token"
        with self.assertRaisesRegex(Error, "another registry origin"):
            self.registry.manifest(self.repository + ":absent")
        self.credentials.assert_not_called()
        self.assertTrue(all(r.url.host == "ghcr.io" for r in self.server.requests))

    def test_foreign_upload_location_is_rejected_without_forwarding_token(self):
        self.server.location = "https://example.invalid/upload"
        with self.assertRaisesRegex(Error, "another origin"):
            self.publish()
        self.assertTrue(all(r.url.host == "ghcr.io" for r in self.server.requests))
        self.assertEqual(self.server.manifests, {})

    def test_failed_blob_upload_never_publishes_a_chart(self):
        self.server.fail_upload = True
        with self.assertRaisesRegex(Error, "500"):
            self.publish()
        self.assertEqual(self.server.manifests, {})

    def test_digest_mismatch_cannot_become_an_alias(self):
        digest = self.publish()
        self.server.manifests[digest] += b" "
        with self.assertRaisesRegex(Error, "different chart digest"):
            self.registry.alias(self.repository, digest, "feat")
        self.assertNotIn("feat", self.server.manifests)

    def test_network_failure_does_not_expose_request_credentials(self):
        client = httpx.Client(
            transport=httpx.MockTransport(
                lambda request: (_ for _ in ()).throw(
                    httpx.ConnectError("sensitive-url-token")
                )
            )
        )
        with ChartRegistry(self.repository, client=client) as registry:
            with self.assertRaises(Error) as raised:
                registry.manifest(self.repository + ":absent")
        self.assertNotIn("sensitive-url-token", str(raised.exception))


class DockerCredentialsTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(
            patch.dict(os.environ, {"DOCKER_CONFIG": str(self.directory)})
        )

    def config(self, data):
        (self.directory / "config.json").write_text(json.dumps(data))

    def test_inline_credentials_are_scoped_to_the_requested_host(self):
        self.config(
            {
                "auths": {
                    "ghcr.io": {
                        "auth": base64.b64encode(b"user:secret:with-colon").decode()
                    }
                }
            }
        )
        self.assertEqual(docker_credentials("ghcr.io"), ("user", "secret:with-colon"))
        self.assertIsNone(docker_credentials("another.invalid"))

    def test_per_registry_helper_takes_precedence_over_global_store(self):
        self.config({"credsStore": "global", "credHelpers": {"ghcr.io": "desktop"}})
        with patch(
            "scripts.cicd.chart_registry.subprocess.run",
            return_value=Mock(
                returncode=0, stdout='{"Username":"user","Secret":"secret"}'
            ),
        ) as helper:
            self.assertEqual(docker_credentials("ghcr.io"), ("user", "secret"))
        self.assertEqual(helper.call_args.args[0], ["docker-credential-desktop", "get"])
        self.assertEqual(helper.call_args.kwargs["input"], "ghcr.io\n")

    def test_helper_failure_does_not_print_secrets(self):
        self.config({"credsStore": "desktop"})
        with patch(
            "scripts.cicd.chart_registry.subprocess.run",
            return_value=Mock(
                returncode=1, stdout="private-token", stderr="private-password"
            ),
        ):
            with self.assertRaises(Error) as raised:
                docker_credentials("ghcr.io")
        self.assertIn("docker login ghcr.io", str(raised.exception))
        self.assertNotIn("private", str(raised.exception))

    def test_missing_configuration_allows_anonymous_lookup(self):
        self.assertIsNone(docker_credentials("ghcr.io"))
