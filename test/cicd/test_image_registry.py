"""Docker Buildx registry responses, authentication failures and digest consistency."""

import json
import unittest
from unittest.mock import Mock, patch

from scripts.cicd.common import Error
from scripts.cicd.image_registry import DockerImageRegistry


class DockerImageRegistryTests(unittest.TestCase):
    ref = "ghcr.io/example/api:feat-12345678"

    def setUp(self):
        self.registry = DockerImageRegistry()
        self.manifest = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.oci.image.index.v1+json",
            "digest": "sha256:" + "a" * 64,
            "annotations": {
                "org.opencontainers.image.revision": "12345678" + "b" * 32,
                "org.opencontainers.image.version": "0.1.0",
            },
            "manifests": [],
        }
        self.process = self.enterContext(patch("scripts.cicd.image_registry.run"))
        self.process.return_value = Mock(returncode=0, stdout=json.dumps(self.manifest))

    def test_annotations_and_digest_come_from_the_same_response(self):
        self.assertEqual(self.registry.manifest(self.ref), self.manifest)
        self.assertEqual(self.registry.digest(self.ref), self.manifest["digest"])
        self.process.assert_called_once_with(
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            "--format",
            "{{json .Manifest}}",
            self.ref,
            check=False,
        )

    def test_digest_without_a_prior_lookup_resolves_the_manifest(self):
        self.assertEqual(self.registry.digest(self.ref), self.manifest["digest"])
        self.process.assert_called_once()

    def test_missing_tags_are_not_cached_and_can_become_visible(self):
        for error in (
            f"ERROR: {self.ref}: not found\n",
            "manifest unknown",
            "MANIFEST_UNKNOWN",
        ):
            with self.subTest(error=error):
                self.process.return_value = Mock(returncode=1, stderr=error)
                self.assertIsNone(self.registry.manifest(self.ref))
                with self.assertRaisesRegex(Error, "Image manifest is missing"):
                    self.registry.digest(self.ref)
        self.process.return_value = Mock(returncode=0, stdout=json.dumps(self.manifest))
        self.assertEqual(self.registry.manifest(self.ref), self.manifest)
        self.assertEqual(self.registry.digest(self.ref), self.manifest["digest"])

    def test_new_lookup_invalidates_the_previous_digest(self):
        self.registry.manifest(self.ref)
        self.process.return_value = Mock(
            returncode=1, stderr=f"ERROR: {self.ref}: not found"
        )
        self.assertIsNone(self.registry.manifest(self.ref))
        with self.assertRaisesRegex(Error, "Image manifest is missing"):
            self.registry.digest(self.ref)

    def test_status_digits_in_a_tag_are_not_an_authentication_failure(self):
        ref = "ghcr.io/example/api:feat-401403aa"
        self.process.return_value = Mock(returncode=1, stderr=f"ERROR: {ref}: not found")
        self.assertIsNone(self.registry.manifest(ref))

    def test_access_network_and_helper_failures_are_not_missing_images(self):
        for error in (
            "401 Unauthorized",
            "403 Forbidden",
            "denied: manifest unknown",
            "failed to authorize: token endpoint returned 404 Not Found",
            'error getting credentials: executable "docker-credential-test" not found',
            "connection refused",
            "TLS handshake timeout",
            "manifest child not found",
        ):
            with self.subTest(error=error):
                self.process.return_value = Mock(returncode=1, stderr=error)
                with self.assertRaisesRegex(Error, "Registry lookup failed"):
                    self.registry.manifest(self.ref)

    def test_malformed_output_does_not_produce_an_image_identity(self):
        for output in ("not json", "null", "[]", "{}", '{"digest": "wrong"}'):
            with self.subTest(output=output):
                self.process.return_value = Mock(returncode=0, stdout=output)
                with self.assertRaisesRegex(Error, "invalid manifest"):
                    self.registry.manifest(self.ref)
