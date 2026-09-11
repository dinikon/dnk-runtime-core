"""Parallel image publication, visibility waits and immutable tag validation."""

from unittest.mock import Mock, patch as mock_patch
import unittest

from scripts.cicd.common import Error, ROOT
from scripts.cicd.images import publish_images
from scripts.cicd.registry import Registry, wait_for_manifest
from test.cicd.support import MemoryRegistry


class ArtifactTests(unittest.TestCase):
    prefix = "registry.example/runtime"
    app = "0.1.0-rc.1"
    source = "12345678" + "a" * 32

    def setUp(self):
        self.sleep = self.enterContext(mock_patch("scripts.cicd.registry.time.sleep"))

    def save_image(self, registry, target, tag, source=None):
        registry.save(
            f"{self.prefix}/{target}:{tag}",
            {
                "annotations": {
                    "org.opencontainers.image.revision": source or self.source,
                    "org.opencontainers.image.version": self.app,
                }
            },
        )

    def publish(self, registry, builder, tag=None, source=None):
        return publish_images(
            ROOT,
            registry,
            self.prefix,
            self.app,
            source or self.source,
            tag or self.app,
            builder,
        )

    def test_partial_batch_failure_reuses_either_image_on_retry(self):
        for completed, missing in (
            ("runtime", "frontend-runtime"),
            ("frontend-runtime", "runtime"),
        ):
            with self.subTest(completed=completed):
                registry = MemoryRegistry()

                def fail_batch(root, targets, env):
                    self.assertEqual(targets, ["runtime", "frontend-runtime"])
                    self.assertEqual(env["IMAGE_TAG"], self.app)
                    self.save_image(registry, completed, env["IMAGE_TAG"])
                    raise Error("one parallel build failed")

                with self.assertRaisesRegex(Error, "parallel build failed"):
                    self.publish(registry, fail_batch)
                saved = registry.digest(f"{self.prefix}/{completed}:{self.app}")

                def retry(root, targets, env):
                    self.assertEqual(targets, [missing])
                    self.save_image(registry, missing, env["IMAGE_TAG"])

                result = self.publish(registry, retry)
                self.assertEqual(result[completed]["digest"], saved)
                builder = Mock(side_effect=AssertionError("Images already exist"))
                self.assertEqual(self.publish(registry, builder), result)
                builder.assert_not_called()

    def test_short_sha_collision_is_rejected_without_overwrite(self):
        registry = MemoryRegistry()
        tag = "dev-12345678"
        self.save_image(registry, "runtime", tag)
        original = registry.digest(f"{self.prefix}/runtime:{tag}")
        builder = Mock()
        with self.assertRaisesRegex(Error, "different source/version"):
            self.publish(registry, builder, tag=tag, source="12345678" + "b" * 32)
        builder.assert_not_called()
        self.assertEqual(registry.digest(f"{self.prefix}/runtime:{tag}"), original)

    def test_unrelated_version_tag_prevents_build(self):
        registry = MemoryRegistry()
        self.save_image(registry, "runtime", self.app, source="another-source")
        builder = Mock()
        with self.assertRaisesRegex(Error, "different source/version"):
            self.publish(registry, builder)
        builder.assert_not_called()

    def test_successful_builder_must_publish_every_requested_image(self):
        registry = MemoryRegistry()

        def incomplete(root, targets, env):
            self.save_image(registry, "runtime", env["IMAGE_TAG"])

        with self.assertRaisesRegex(
            Error, "still does not expose .*frontend-runtime:0.1.0-rc.1"
        ):
            self.publish(registry, incomplete)

    def test_successful_push_waits_for_tag_visibility(self):
        registry = MemoryRegistry()
        pending = {}
        manifest = registry.manifest

        def delayed(ref):
            if pending.get(ref, 0):
                pending[ref] -= 1
                return None
            return manifest(ref)

        registry.manifest = delayed

        def build(root, targets, env):
            for target in targets:
                self.save_image(registry, target, env["IMAGE_TAG"])
                pending[f"{self.prefix}/{target}:{env['IMAGE_TAG']}"] = 2

        result = self.publish(registry, build)
        self.assertEqual(set(result), {"runtime", "frontend-runtime"})
        self.assertEqual(self.sleep.call_count, 4)
        builder = Mock(side_effect=AssertionError("Images already published"))
        self.assertEqual(self.publish(registry, builder), result)
        builder.assert_not_called()

    def test_partial_failure_recovers_image_that_is_not_immediately_visible(self):
        registry = MemoryRegistry()
        manifest = registry.manifest
        pending = []

        def delayed(ref):
            if pending and "/runtime:" in ref:
                pending.pop()
                return None
            return manifest(ref)

        registry.manifest = delayed

        def build(root, targets, env):
            self.save_image(registry, "runtime", env["IMAGE_TAG"])
            pending.extend([None, None])
            raise Error("frontend build failed")

        with self.assertRaisesRegex(Error, "frontend build failed"):
            self.publish(registry, build)
        self.assertIsNotNone(manifest(f"{self.prefix}/runtime:{self.app}"))
        self.assertIsNone(manifest(f"{self.prefix}/frontend-runtime:{self.app}"))

    def test_missing_manifest_wait_is_bounded_and_reports_exact_reference(self):
        registry = Mock()
        registry.manifest.return_value = None
        ref = "registry.example/runtime:dev-12345678"
        with self.assertRaisesRegex(Error, ref + " after 7 checks"):
            wait_for_manifest(registry, ref)
        self.assertEqual(registry.manifest.call_count, 7)
        self.assertEqual(sum(call.args[0] for call in self.sleep.call_args_list), 60)

    def test_alias_wait_requires_expected_digest(self):
        registry = Mock()
        registry.manifest.return_value = {"schemaVersion": 2}
        registry.digest.side_effect = ["sha256:old", "sha256:old", "sha256:new"]
        wait_for_manifest(registry, "registry/runtime:latest", digest="sha256:new")
        self.assertEqual(self.sleep.call_count, 2)

    def test_manifest_wait_does_not_retry_registry_auth_failure(self):
        registry = Mock()
        registry.manifest.side_effect = Error("denied: requested access")
        with self.assertRaisesRegex(Error, "denied"):
            wait_for_manifest(registry, "registry.example/runtime:version")
        registry.manifest.assert_called_once()
        self.sleep.assert_not_called()

    def test_delayed_wrong_image_is_rejected(self):
        registry = MemoryRegistry()
        manifest = registry.manifest
        pending = []

        def delayed(ref):
            if pending:
                pending.pop()
                return None
            return manifest(ref)

        registry.manifest = delayed

        def build(root, targets, env):
            self.save_image(registry, "runtime", env["IMAGE_TAG"], source="wrong")
            pending.append(None)

        with self.assertRaisesRegex(Error, "different source/version"):
            self.publish(registry, build)

    def test_registry_auth_failure_is_not_treated_as_missing_version(self):
        with mock_patch(
            "scripts.cicd.registry.run",
            return_value=Mock(returncode=1, stderr="401 Unauthorized"),
        ):
            with self.assertRaisesRegex(
                Error, "Registry lookup failed for registry/chart:0.1.0"
            ):
                Registry().manifest("registry/chart:0.1.0")
