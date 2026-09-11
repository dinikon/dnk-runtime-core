"""Publication retries and packaged Helm image references."""

from pathlib import Path
import tarfile
import tempfile

import yaml

from scripts.cicd.artifacts import publish_artifacts
from scripts.cicd.charts import package_chart
from scripts.cicd.common import Error
from scripts.cicd.gitops import start_release
from test.cicd.support import MemoryRegistry, ReleaseRepoTestCase


class ArtifactTests(ReleaseRepoTestCase):
    def test_artifact_retry_reuses_partial_images_and_complete_chart(self):
        start_release(self.repo)
        tag = self.rc()
        registry = MemoryRegistry()
        calls = []
        fail = [True]

        def builder(root, targets, env):
            calls.append(tuple(targets))
            for target in targets:
                if target == "frontend-runtime" and fail[0]:
                    fail[0] = False
                    raise Error("simulated frontend build failure")
                ref = env["REGISTRY_PREFIX"] + "/" + target + ":" + env["IMAGE_TAG"]
                registry.save(
                    ref,
                    {
                        "annotations": {
                            "org.opencontainers.image.revision": env["SOURCE_REVISION"],
                            "org.opencontainers.image.version": env["VERSION"],
                        }
                    },
                )

        args = (self.repo, tag, self.repo.branch(), self.repo.sha(), "123", "1")
        with self.assertRaisesRegex(Error, "simulated"):
            publish_artifacts(*args, registry=registry, builder=builder)
        self.assertEqual(registry.chart_pushes, 0)
        record = publish_artifacts(*args[:-1], "2", registry=registry, builder=builder)
        again = publish_artifacts(*args[:-1], "3", registry=registry, builder=builder)
        self.assertEqual(record, again)
        self.assertEqual(
            calls, [("runtime", "frontend-runtime"), ("frontend-runtime",)]
        )
        self.assertEqual(registry.chart_pushes, 1)
        with (
            self.repo.checkout(tag) as checkout,
            tempfile.TemporaryDirectory() as directory,
        ):
            archive, _ = package_chart(checkout.root, Path(directory), record)
            with tarfile.open(archive) as tar:
                values = yaml.safe_load(tar.extractfile("dnk-runtime-core/values.yaml"))
                chart = yaml.safe_load(tar.extractfile("dnk-runtime-core/Chart.yaml"))
                self.assertEqual(chart["version"], "0.3.3-rc.1")
                self.assertEqual(chart["appVersion"], "0.1.0-rc.1")
                for component in [
                    values["backend"],
                    values["frontend"],
                    *values["workers"].values(),
                ]:
                    self.assertEqual(component["image"]["tag"], "0.1.0-rc.1")
                    self.assertIn("pullPolicy", component["image"])
                self.assertTrue(
                    any("charts/postgresql/" in name for name in tar.getnames())
                )

    def test_dev_short_tag_is_reused_across_runs_and_pinned_in_chart(self):
        source = self.repo.sha()
        expected_tag = "dev-" + source[:8]
        registry = MemoryRegistry()
        builds = []

        def builder(root, targets, env):
            builds.append(tuple(targets))
            self.assertEqual(env["IMAGE_TAG"], expected_tag)
            for target in targets:
                registry.save(
                    env["REGISTRY_PREFIX"] + "/" + target + ":" + env["IMAGE_TAG"],
                    {
                        "annotations": {
                            "org.opencontainers.image.revision": source,
                            "org.opencontainers.image.version": env["VERSION"],
                        }
                    },
                )

        first = publish_artifacts(
            self.repo,
            source,
            "develop",
            source,
            "123",
            "1",
            registry=registry,
            builder=builder,
        )
        again = publish_artifacts(
            self.repo,
            source,
            "develop",
            source,
            "124",
            "2",
            registry=registry,
            builder=builder,
        )
        self.assertEqual(builds, [("runtime", "frontend-runtime")])
        self.assertEqual(first["images"], again["images"])
        self.assertNotEqual(first["chart_version"], again["chart_version"])
        with tempfile.TemporaryDirectory() as directory:
            archive, _ = package_chart(self.root, Path(directory), again)
            with tarfile.open(archive) as tar:
                values = yaml.safe_load(tar.extractfile("dnk-runtime-core/values.yaml"))
            for component in [
                values["backend"],
                values["frontend"],
                *values["workers"].values(),
            ]:
                self.assertEqual(component["image"]["tag"], expected_tag)
