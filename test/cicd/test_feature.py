"""Feature publication guards and retries using real Git and a fake registry."""

from contextlib import nullcontext
import json
import os
import tarfile
import yaml
from unittest.mock import Mock, patch

from scripts.cicd.__main__ import main
from scripts.cicd.common import Error, run
from scripts.cicd.feature import CHART_REPOSITORY, IMAGE_PREFIX, publish_feature
from scripts.cicd.registry import PUBLICATION
from scripts.cicd.repository import Repo
from test.cicd.support import MemoryRegistry, ReleaseRepoTestCase


class FeatureTests(ReleaseRepoTestCase):
    targets = ("runtime", "frontend-runtime")

    def setUp(self):
        super().setUp()
        self.branch = "feature/team/example"
        self.repo.git("switch", "-c", self.branch)
        self.source = self.repo.sha()
        self.tag = "feat-" + self.source[:8]
        self.chart_version = "0.3.2-feat.g" + self.source[:8]
        self.chart_ref = CHART_REPOSITORY + ":" + self.chart_version
        self.refs = self.repo.git("show-ref").stdout
        self.worktrees = self.repo.git("worktree", "list", "--porcelain").stdout
        self.registry = MemoryRegistry()
        self.alias = self.enterContext(
            patch.object(self.registry, "alias", wraps=self.registry.alias)
        )
        self.lookup = self.enterContext(
            patch.object(self.registry, "manifest", wraps=self.registry.manifest)
        )
        self.tools = self.enterContext(
            patch("scripts.cicd.feature.shutil.which", side_effect=lambda name: name)
        )
        self.buildx = self.enterContext(
            patch("scripts.cicd.feature.run", return_value=Mock(returncode=0))
        )
        self.builder = Mock(side_effect=self.build)
        self.build_roots = []

    def save(self, target, source=None):
        self.registry.save(
            IMAGE_PREFIX + "/" + target + ":" + self.tag,
            {
                "annotations": {
                    "org.opencontainers.image.revision": source or self.source,
                    "org.opencontainers.image.version": "0.1.0",
                }
            },
        )

    def build(self, root, targets, environment):
        self.build_roots.append(root)
        self.assertNotEqual(root, self.root)
        self.assertEqual(Repo(root).sha(), self.source)
        self.assertEqual(environment["REGISTRY_PREFIX"], IMAGE_PREFIX)
        self.assertEqual(environment["IMAGE_TAG"], self.tag)
        self.assertRegex(environment["IMAGE_TAG"], r"^feat-[0-9a-f]{8}$")
        self.assertEqual(environment["SOURCE_REVISION"], self.source)
        self.assertEqual(
            environment["SOURCE_URL"], "https://github.com/dinikon/dnk-runtime-core"
        )
        self.assertEqual(environment["VERSION"], "0.1.0")
        self.assertEqual(environment["BRANCH"], self.branch)
        self.assertEqual(environment["PLATFORMS"], "linux/amd64,linux/arm64")
        for target in targets:
            self.save(target)

    def publish(self):
        return publish_feature(
            self.repo,
            registry=self.registry,
            chart_registry=self.registry,
            builder=self.builder,
        )

    def assert_untouched(self):
        self.assertEqual(self.repo.git("show-ref").stdout, self.refs)
        self.assertEqual(
            self.repo.git("worktree", "list", "--porcelain").stdout, self.worktrees
        )
        for root in self.build_roots:
            self.assertFalse(root.exists())

    def assert_rejected(self, message):
        self.tools.reset_mock()
        with self.assertRaisesRegex(Error, message):
            self.publish()
        self.tools.assert_not_called()
        self.buildx.assert_not_called()
        self.lookup.assert_not_called()
        self.builder.assert_not_called()
        self.alias.assert_not_called()
        self.assertEqual(self.registry.chart_pushes, 0)

    def test_publishes_both_images_and_reports_verified_digests(self):
        with self.assertLogs("scripts.cicd", level="INFO") as logs:
            record = self.publish()
        images = record["images"]
        self.assertEqual(set(images), set(self.targets))
        self.builder.assert_called_once()
        self.assertEqual(self.builder.call_args.args[1], list(self.targets))
        for image in images.values():
            ref = image["repository"] + ":" + self.tag
            self.assertEqual(image["tag"], self.tag)
            self.assertEqual(image["digest"], self.registry.digest(ref))
            self.assertTrue(
                any(ref in line and image["digest"] in line for line in logs.output)
            )
        self.assert_untouched()
        self.assertEqual(record["chart_version"], self.chart_version)
        self.assertEqual(
            record["chart_digest"], self.registry.digest(CHART_REPOSITORY + ":feat")
        )
        self.assertEqual(self.registry.chart_pushes, 1)
        self.alias.assert_called_once()
        self.repo.clean()

    def test_rejects_other_branches_and_detached_head_before_external_tools(self):
        for branch in (
            "main",
            "develop",
            "release/1.0.0",
            "hotfix/fix",
            "featureish/test",
        ):
            with self.subTest(branch=branch):
                self.repo.git("switch", "-C", branch)
                self.assert_rejected(r"requires a feature/\* branch")
        self.repo.git("switch", "--detach")
        self.assert_rejected("detached HEAD")

    def test_rejects_empty_feature_suffix(self):
        with patch.object(
            self.repo, "git", return_value=Mock(returncode=0, stdout="feature/\n")
        ):
            self.assert_rejected(r"requires a feature/\* branch")

    def test_rejects_all_uncommitted_changes_even_when_untracked_files_are_hidden(self):
        for state in (
            "unstaged",
            "staged",
            "deleted",
            "staged-deleted",
            "untracked",
            "hidden-untracked",
            "staged-new",
        ):
            with self.subTest(state=state):
                tracked = self.root / "feature.txt"
                new = self.root / "untracked.txt"
                if state in ("deleted", "staged-deleted"):
                    tracked.unlink()
                elif state in ("unstaged", "staged"):
                    tracked.write_text("uncommitted change")
                else:
                    new.write_text("new file")
                if state.startswith("staged"):
                    self.repo.git("add", "-A")
                if state == "hidden-untracked":
                    self.repo.git("config", "status.showUntrackedFiles", "no")
                    self.assertEqual(self.repo.git("status", "--porcelain").stdout, "")
                self.assert_rejected("Commit or remove local changes first")
                self.repo.git("reset", "--hard", "HEAD")
                new.unlink(missing_ok=True)
        self.assert_untouched()

    def test_rejects_unresolved_merge(self):
        self.repo.git("switch", "-c", "conflicting")
        self.commit("fix: first change", "feature.txt", "first")
        self.repo.git("switch", self.branch)
        self.commit("fix: second change", "feature.txt", "second")
        result = self.repo.git("merge", "conflicting", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assert_rejected("resolve and commit any merge conflict")

    def test_build_is_pinned_and_excludes_ignored_files(self):
        ignored = self.root / "local-only.txt"
        (self.root / ".git/info/exclude").write_text("local-only.txt\n")
        ignored.write_text("local artifact")
        committed = (self.root / "feature.txt").read_text()

        def build(root, targets, environment):
            # A user edit after the initial guard must not enter the build context.
            (self.root / "feature.txt").write_text("edited while building")
            self.assertEqual((root / "feature.txt").read_text(), committed)
            self.assertFalse((root / ignored.name).exists())
            self.build(root, targets, environment)

        self.builder.side_effect = build
        self.publish()
        self.assertEqual(
            (self.root / "feature.txt").read_text(), "edited while building"
        )
        self.assert_untouched()

    def test_missing_tools_and_buildx_fail_before_registry(self):
        for missing in ("docker", "helm"):
            with self.subTest(missing=missing):
                self.tools.side_effect = lambda name: None if name == missing else name
                with self.assertRaisesRegex(Error, "Install " + missing + " first"):
                    self.publish()
        self.tools.side_effect = lambda name: name
        self.buildx.return_value.returncode = 1
        with self.assertRaisesRegex(Error, "Docker Buildx is required"):
            self.publish()
        self.lookup.assert_not_called()
        self.builder.assert_not_called()
        self.assert_untouched()

    def test_retry_reuses_completed_images(self):
        first = self.publish()
        self.builder.reset_mock()
        self.assertEqual(self.publish(), first)
        self.builder.assert_not_called()
        self.assert_untouched()

    def test_partial_push_failure_cleans_worktree_and_retry_builds_only_missing(self):
        def partial(root, targets, environment):
            self.build(root, targets[:1], environment)
            raise Error("simulated push failure")

        self.builder.side_effect = partial
        with self.assertRaisesRegex(Error, "simulated push failure"):
            self.publish()
        self.assert_untouched()
        self.builder.reset_mock(side_effect=True)
        self.builder.side_effect = self.build
        self.publish()
        self.assertEqual(self.builder.call_args.args[1], [self.targets[1]])
        self.assert_untouched()

    def test_short_sha_collision_is_never_overwritten(self):
        self.save(self.targets[0], self.source[:8] + "f" * 32)
        before = dict(self.registry.digests)
        with self.assertRaisesRegex(Error, "different source/version"):
            self.publish()
        self.builder.assert_not_called()
        self.assertEqual(self.registry.digests, before)
        self.assert_untouched()

    def test_registry_denial_cleans_worktree_without_building(self):
        self.lookup.side_effect = Error("401 Unauthorized")
        with self.assertRaisesRegex(Error, "401 Unauthorized"):
            self.publish()
        self.builder.assert_not_called()
        self.assert_untouched()

    def test_default_builder_uses_push_and_overrides_inherited_identity(self):
        def bake(*args, cwd, env):
            self.assertEqual(args[:3], ("docker", "buildx", "bake"))
            self.assertIn("--push", args)
            self.assertIn("--progress=plain", args)
            self.assertTrue(any(".cache-to=" in arg for arg in args))
            self.build(cwd, list(self.targets), env)

        with (
            patch.dict(
                os.environ,
                {
                    "BRANCH": "develop",
                    "REGISTRY_PREFIX": "registry.invalid/wrong",
                    "IMAGE_TAG": "latest",
                    "SOURCE_REVISION": "wrong",
                    "SOURCE_URL": "https://example.invalid/wrong",
                    "VERSION": "wrong",
                    "PLATFORMS": "linux/arm64",
                    "CICD_BUILD_CACHE": "registry",
                },
            ),
            patch("scripts.cicd.images.live", side_effect=bake) as process,
        ):
            publish_feature(
                self.repo, registry=self.registry, chart_registry=self.registry
            )
        process.assert_called_once()
        self.assert_untouched()

    def test_cli_dispatch_and_error_exit_code(self):
        with (
            patch("scripts.cicd.__main__.ROOT", self.root),
            patch("scripts.cicd.__main__.configure_logging"),
            patch("sys.argv", ["cicd", "publish-feature"]),
            patch(
                "scripts.cicd.feature.DockerImageRegistry", return_value=self.registry
            ),
            patch(
                "scripts.cicd.feature.ChartRegistry",
                return_value=nullcontext(self.registry),
            ),
            patch("scripts.cicd.feature.build_images", self.builder),
        ):
            self.assertEqual(main(), 0)
            self.repo.git("switch", "develop")
            with self.assertLogs("scripts.cicd", level="ERROR") as logs:
                self.assertEqual(main(), 1)
            self.assertIn("requires a feature/* branch", logs.output[0])
        self.builder.assert_called_once()

    def test_default_registry_publishes_and_retries_without_oras(self):
        self.tools.side_effect = lambda name: (
            name if name in ("docker", "helm") else None
        )

        def inspect(*args, check):
            self.assertEqual(args[:4], ("docker", "buildx", "imagetools", "inspect"))
            self.assertFalse(check)
            ref = args[-1]
            manifest = self.registry.manifest(ref)
            if manifest is None:
                return Mock(returncode=1, stderr=f"ERROR: {ref}: not found\n")
            return Mock(
                returncode=0,
                stdout=json.dumps(manifest | {"digest": self.registry.digest(ref)}),
            )

        with patch("scripts.cicd.image_registry.run", side_effect=inspect):
            first = publish_feature(
                self.repo, chart_registry=self.registry, builder=self.builder
            )
            again = publish_feature(
                self.repo, chart_registry=self.registry, builder=self.builder
            )
        self.assertEqual(first, again)
        self.assertEqual(set(first["images"]), set(self.targets))
        self.builder.assert_called_once()
        self.assertTrue(
            all(
                call.args in (("docker",), ("helm",))
                for call in self.tools.call_args_list
            )
        )
        self.assert_untouched()

    def test_chart_contains_feature_images_and_a_new_deployment_revision(self):
        original = self.registry.push_chart
        chart_source = (self.root / "helm/Chart.yaml").read_bytes()

        def push(repository, archive, config, record):
            metadata = yaml.safe_load(config.read_text())
            self.assertEqual(metadata["version"], self.chart_version)
            self.assertEqual(metadata["appVersion"], "0.1.0")
            with tarfile.open(archive) as package:
                values = yaml.safe_load(
                    package.extractfile(metadata["name"] + "/values.yaml")
                )
                embedded = json.load(
                    package.extractfile(metadata["name"] + "/publication.json")
                )
            self.assertEqual(embedded, record)
            for component in (
                values["backend"],
                values["frontend"],
                *values.get("workers", {}).values(),
            ):
                self.assertEqual(component["image"]["tag"], self.tag)
            self.assertEqual(
                values["global"]["deployment"]["revision"], "feat-" + self.source
            )
            rendered = run(
                "helm",
                "template",
                "feature-test",
                archive,
                "-f",
                self.root / "helm/examples/values-embedded.yaml",
            ).stdout
            self.assertIn(":" + self.tag, rendered)
            self.assertIn("feat-" + self.source, rendered)
            self.alias.assert_not_called()
            return original(repository, archive, config, record)

        with patch.object(self.registry, "push_chart", side_effect=push):
            self.publish()
        self.assertEqual((self.root / "helm/Chart.yaml").read_bytes(), chart_source)
        self.assert_untouched()

    def test_chart_push_failure_preserves_alias_and_reuses_images_on_retry(self):
        self.registry.save(CHART_REPOSITORY + ":feat", {"old": True})
        previous = self.registry.digest(CHART_REPOSITORY + ":feat")
        with patch.object(
            self.registry, "push_chart", side_effect=Error("chart upload failed")
        ):
            with self.assertRaisesRegex(Error, "chart upload failed"):
                self.publish()
        self.alias.assert_not_called()
        self.assertEqual(self.registry.digest(CHART_REPOSITORY + ":feat"), previous)
        self.publish()
        self.builder.assert_called_once()
        self.assertEqual(self.registry.chart_pushes, 1)
        self.assert_untouched()

    def test_alias_failure_reuses_the_complete_chart(self):
        self.alias.side_effect = Error("alias push failed")
        with self.assertRaisesRegex(Error, "alias push failed"):
            self.publish()
        self.assertEqual(self.registry.chart_pushes, 1)
        self.alias.side_effect = None
        self.publish()
        self.builder.assert_called_once()
        self.assertEqual(self.registry.chart_pushes, 1)
        self.assert_untouched()

    def test_changed_head_does_not_move_feat(self):
        def build(root, targets, environment):
            self.build(root, targets, environment)
            self.commit("feat: newer local commit")

        self.builder.side_effect = build
        with self.assertRaisesRegex(Error, "Branch/HEAD changed"):
            self.publish()
        self.alias.assert_not_called()
        self.assertIsNotNone(self.registry.manifest(self.chart_ref))

    def test_existing_chart_with_wrong_identity_is_not_overwritten(self):
        record = self.publish()
        self.alias.reset_mock()
        record["source_sha"] = "other-commit"
        self.registry.save(
            self.chart_ref, {"annotations": {PUBLICATION: json.dumps(record)}}
        )
        with self.assertRaisesRegex(Error, "differs in source_sha"):
            self.publish()
        self.alias.assert_not_called()
        self.assertEqual(self.registry.chart_pushes, 1)

    def test_same_commit_from_another_feature_branch_reuses_the_chart(self):
        self.publish()
        self.repo.git("switch", "-c", "feature/another")
        self.publish()
        self.builder.assert_called_once()
        self.assertEqual(self.registry.chart_pushes, 1)
