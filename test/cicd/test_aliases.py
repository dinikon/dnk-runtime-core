"""Channel alias ordering, stale-run protection and recovery."""

from unittest.mock import Mock, patch as mock_patch
import unittest

from scripts.cicd.aliases import publish_channel_aliases
from scripts.cicd.common import Error
from test.cicd.support import MemoryRegistry


class ChannelAliasTests(unittest.TestCase):
    def setUp(self):
        self.repo = Mock()
        self.repo.sha.return_value = "head"
        self.registry = MemoryRegistry()
        self.record = {
            "channel": "stable",
            "branch": "main",
            "build_sha": "head",
            "chart_repository": "registry/helm",
            "chart_digest": "sha256:chart",
            "images": {},
        }
        self.registry.save("registry/helm:0.3.3", {"version": "0.3.3"})
        self.record["chart_digest"] = self.registry.digest("registry/helm:0.3.3")
        for target in ("runtime", "frontend-runtime"):
            repository = "registry/" + target
            self.registry.save(
                repository + ":0.1.0", {"image": target, "version": "0.1.0"}
            )
            self.record["images"][target] = {
                "repository": repository,
                "tag": "0.1.0",
                "digest": self.registry.digest(repository + ":0.1.0"),
            }
        self.alias = self.enterContext(
            mock_patch.object(self.registry, "alias", wraps=self.registry.alias)
        )
        self.enterContext(mock_patch("scripts.cicd.registry.time.sleep"))

    def publish(self):
        return publish_channel_aliases(self.repo, self.record, self.registry)

    def test_current_main_updates_both_latest_tags_idempotently(self):
        self.assertTrue(self.publish())
        self.assertEqual(self.alias.call_count, 2)
        for image in self.record["images"].values():
            self.assertEqual(
                self.registry.digest(image["repository"] + ":latest"), image["digest"]
            )
            self.assertEqual(
                self.registry.digest(image["repository"] + ":0.1.0"), image["digest"]
            )
        self.assertIsNone(self.registry.manifest("registry/helm:latest"))
        self.assertTrue(self.publish())
        self.assertEqual(self.alias.call_count, 2)

    def test_dev_only_updates_chart_dev_alias(self):
        self.record.update(channel="dev", branch="develop")
        self.assertTrue(self.publish())
        self.alias.assert_called_once_with(
            "registry/helm", self.record["chart_digest"], "dev"
        )
        for image in self.record["images"].values():
            self.assertIsNone(self.registry.manifest(image["repository"] + ":latest"))

    def test_rc_does_not_touch_floating_tags(self):
        self.record.update(channel="rc", branch="release/0.1.0")
        self.assertFalse(self.publish())
        self.alias.assert_not_called()
        self.repo.fetch.assert_not_called()

    def test_stale_main_and_develop_do_not_move_aliases(self):
        self.repo.sha.return_value = "newer"
        for channel, branch in (("stable", "main"), ("dev", "develop")):
            with self.subTest(channel=channel):
                self.record.update(channel=channel, branch=branch)
                self.assertFalse(self.publish())
        self.alias.assert_not_called()

    def test_head_is_rechecked_before_each_alias(self):
        self.repo.sha.side_effect = ["head", "newer"]
        self.assertFalse(self.publish())
        self.assertEqual(self.alias.call_count, 1)

    def test_retry_completes_partial_latest_update(self):
        original = self.alias._mock_wraps
        failed = [False]

        def partial(repository, digest, tag):
            if repository.endswith("frontend-runtime") and not failed[0]:
                failed[0] = True
                raise Error("registry unavailable")
            original(repository, digest, tag)

        self.alias.side_effect = partial
        with self.assertRaisesRegex(Error, "registry unavailable"):
            self.publish()
        self.assertTrue(self.publish())
        self.assertEqual(self.alias.call_count, 3)
