"""Release transactions use real Git/Commitizen, temporary repos and fake remote APIs."""

import copy
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch as mock_patch

import yaml

from scripts.cicd.artifacts import (
    PUBLICATION,
    Registry,
    package_chart,
    publish_artifacts,
)
from scripts.cicd.common import Error, ROOT, run, versions
from scripts.cicd.delivery import deliver
from scripts.cicd.gitops import (
    Repo,
    prepare_rc,
    publish,
    release_sources,
    start_release,
)


class Releases:
    def __init__(self):
        self.items = {}

    def get_release(self, tag):
        return self.items.get(tag)

    def ready(self, tag, prerelease=True):
        self.items[tag] = {"isPrerelease": prerelease, "isDraft": False}


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="dnk-git-test-")
        self.addCleanup(self.temporary.cleanup)
        parent = Path(self.temporary.name)
        self.root = parent / "repo"
        self.root.mkdir()
        remote = parent / "origin.git"
        run("git", "init", "--bare", remote)
        self.repo = Repo(self.root)
        self.repo.git("init", "-b", "main")
        self.repo.git("config", "user.name", "Local release test")
        self.repo.git("config", "user.email", "test@example.invalid")
        self.repo.git("config", "commit.gpgsign", "false")
        self.repo.git("config", "tag.gpgsign", "false")
        for name in ("pyproject.toml", "uv.lock", "docker-bake.hcl"):
            shutil.copy2(ROOT / name, self.root / name)
        shutil.copytree(
            ROOT / "helm",
            self.root / "helm",
            ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
        )
        (self.root / ".gitignore").write_text("__pycache__/\n.venv/\n")
        self.commit("chore: initial repository", "base.txt")
        self.repo.git("remote", "add", "origin", remote)
        self.repo.git("push", "-u", "origin", "main")
        self.repo.git("switch", "-c", "develop")
        self.commit("feat: initial feature", "feature.txt")
        self.repo.git("push", "-u", "origin", "develop")
        self.github = Releases()

    def commit(self, message, filename="change.txt", text=None):
        (self.root / filename).write_text(text or message)
        self.repo.git("add", ".")
        self.repo.git("commit", "-m", message)
        return self.repo.sha()

    def rc(self, branch=None):
        branch = branch or self.repo.branch()
        self.repo.git("push", "origin", branch)
        self.repo.fetch()
        tag = prepare_rc(self.repo, branch, self.repo.sha())
        self.github.ready(tag)
        return tag

    def initial_release(self):
        start_release(self.repo)
        self.rc()
        publish(self.repo, self.github, lambda: None)
        self.github.ready("v0.1.0", prerelease=False)

    def test_first_rc_and_finalization_retry_after_local_check_failure(self):
        start = self.repo.sha()
        start_release(self.repo)
        self.assertEqual(release_sources(self.repo, self.repo.branch()), [start])
        tag = self.rc()
        self.assertEqual(tag, "v0.1.0-rc.1")
        self.assertEqual(self.repo.sha("HEAD"), start)
        self.assertEqual(self.repo.sha(tag + "^"), start)
        self.assertEqual(prepare_rc(self.repo, self.repo.branch(), start), tag)
        with self.repo.checkout(tag) as rc:
            self.assertEqual(versions(rc.root), ("0.1.0-rc.1", "0.3.3-rc.1"))
        with self.assertRaisesRegex(Error, "simulated"):
            publish(
                self.repo,
                self.github,
                lambda: (_ for _ in ()).throw(Error("simulated check failure")),
            )
        tag_sha = self.repo.sha("v0.1.0")
        self.assertNotEqual(self.repo.sha("origin/main"), tag_sha)
        publish(self.repo, self.github, lambda: None)
        self.assertEqual(self.repo.sha("origin/main"), tag_sha)
        self.assertTrue(self.repo.ancestor(tag_sha, "origin/develop"))
        self.assertEqual(self.repo.chart_at(tag_sha), "0.3.3")
        self.assertIn("v0.1.0-rc.1", self.repo.tags("v*"))

    def test_multiple_commits_one_push_and_docs_only_rc(self):
        start_release(self.repo)
        initial = self.repo.sha()
        first = self.commit("docs: explain release", "readme.txt")
        self.repo.git("switch", "-c", "hotfix/from-release")
        second = self.commit("fix: correct release", "bug.txt")
        self.repo.git("switch", "release/0.1.0")
        self.repo.git("merge", "--no-ff", "--no-edit", "hotfix/from-release")
        merged = self.repo.sha()
        self.repo.git("push", "origin", "release/0.1.0")
        self.repo.fetch()
        self.assertEqual(
            release_sources(self.repo, "release/0.1.0"),
            [initial, first, second, merged],
        )
        for number, source in enumerate(release_sources(self.repo, "release/0.1.0"), 1):
            tag = prepare_rc(self.repo, "release/0.1.0", source)
            self.assertEqual(tag, f"v0.1.0-rc.{number}")
            self.assertEqual(self.repo.metadata(tag)["source_sha"], source)
        self.assertEqual(self.repo.sha("origin/release/0.1.0"), merged)

    def test_patch_hotfix_and_active_release_rename(self):
        self.initial_release()
        self.commit("fix: upcoming fix", "upcoming.txt")
        self.repo.git("push", "origin", "develop")
        start_release(self.repo)
        self.assertEqual(self.repo.branch(), "release/0.1.1")
        self.rc()
        self.repo.git("switch", "-c", "hotfix/urgent", "main")
        self.commit("fix: urgent fix", "urgent.txt")
        publish(self.repo, self.github, lambda: None)
        self.github.ready("v0.1.1", prerelease=False)
        self.assertEqual(self.repo.chart_at("v0.1.1"), "0.3.4")
        self.repo.git("switch", "release/0.1.1")
        self.repo.git("merge", "--no-ff", "--no-edit", "main")
        start_release(self.repo)
        self.assertEqual(self.repo.branch(), "release/0.1.2")
        tag = self.rc()
        self.assertEqual(tag, "v0.1.2-rc.1")
        self.assertEqual(self.repo.metadata(tag)["chart_version"], "0.3.5-rc.1")
        self.assertTrue(self.repo.exists("refs/tags/v0.1.1-rc.1"))

    def test_backmerge_conflict_stops_push_and_can_resume(self):
        start_release(self.repo)
        self.commit("fix: release change", "feature.txt", "release content")
        self.rc()
        self.repo.git("switch", "develop")
        self.commit("feat: next feature", "feature.txt", "develop content")
        self.repo.git("push", "origin", "develop")
        self.repo.git("switch", "release/0.1.0")
        old_main = self.repo.sha("origin/main")
        with self.assertRaises(Error):
            publish(self.repo, self.github, lambda: None)
        self.assertEqual(self.repo.sha("origin/main"), old_main)
        self.assertTrue(self.repo.git("ls-files", "-u").stdout)
        self.commit("fix: resolve backmerge", "feature.txt", "both changes resolved")
        publish(self.repo, self.github, lambda: None)
        self.assertEqual(self.repo.sha("origin/main"), self.repo.sha("v0.1.0"))

    def test_no_release_bump_for_docs_only_after_stable(self):
        self.initial_release()
        self.commit("docs: documentation only")
        self.repo.git("push", "origin", "develop")
        with self.assertRaises(Error):
            start_release(self.repo)

    def test_only_one_release_and_same_series_chart_rebases_after_hotfix(self):
        self.initial_release()
        self.commit("feat: next feature", "next.txt")
        self.repo.git("push", "origin", "develop")
        start_release(self.repo)
        self.assertEqual(self.repo.branch(), "release/0.2.0")
        self.rc()
        self.repo.git("switch", "develop")
        self.commit("feat!: incompatible future change", "future.txt")
        self.repo.git("push", "origin", "develop")
        with self.assertRaisesRegex(Error, "active release/0.2.0"):
            start_release(self.repo)
        self.assertFalse(self.repo.exists("refs/tags/release-start/1.0.0"))
        self.repo.git("switch", "-c", "hotfix/prod", "main")
        self.commit("fix: production bug", "urgent.txt")
        publish(self.repo, self.github, lambda: None)
        self.github.ready("v0.1.1", prerelease=False)
        self.repo.git("switch", "release/0.2.0")
        self.repo.git("merge", "--no-ff", "--no-edit", "main")
        start_release(self.repo)
        tag = self.rc()
        self.assertEqual(tag, "v0.2.0-rc.2")
        self.assertEqual(self.repo.metadata(tag)["chart_version"], "0.3.5-rc.2")

    def test_atomic_push_failure_resumes_without_second_bump(self):
        start_release(self.repo)
        self.rc()
        original = self.repo.git

        def fail_push(*args, **kwargs):
            if args[:2] == ("push", "--atomic"):
                raise Error("simulated atomic push failure")
            return original(*args, **kwargs)

        with mock_patch.object(self.repo, "git", side_effect=fail_push):
            with self.assertRaisesRegex(Error, "atomic push"):
                publish(self.repo, self.github, lambda: None)
        sha = self.repo.sha("v0.1.0")
        publish(
            self.repo,
            self.github,
            lambda: self.fail("Prepared release was already checked"),
        )
        self.assertEqual(self.repo.sha("origin/main"), sha)
        self.assertEqual(self.repo.sha("v0.1.0"), sha)

    def test_artifact_retry_reuses_partial_images_and_complete_chart(self):
        start_release(self.repo)
        tag = self.rc()
        registry = MemoryRegistry()
        calls = []
        fail = [True]

        def builder(root, target, env):
            calls.append(target)
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
        record = publish_artifacts(*args, registry=registry, builder=builder)
        again = publish_artifacts(*args[:-1], "2", registry=registry, builder=builder)
        self.assertEqual(record, again)
        self.assertEqual(calls.count("runtime"), 1)
        self.assertEqual(calls.count("frontend-runtime"), 2)
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


class MemoryRegistry:
    def __init__(self):
        self.manifests = {}
        self.digests = {}
        self.chart_pushes = 0

    def save(self, ref, manifest):
        digest = (
            "sha256:"
            + hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        )
        self.manifests[ref] = manifest
        self.manifests[digest] = manifest
        self.digests[ref] = digest

    def manifest(self, ref):
        return self.manifests.get(ref)

    def digest(self, ref):
        return self.digests[ref]

    def alias(self, repository, digest, tag):
        self.save(repository + ":" + tag, self.manifests[digest])

    def push_chart(self, repository, archive, config, publication):
        self.chart_pushes += 1
        ref = repository + ":" + publication["chart_version"]
        self.save(ref, {"annotations": {PUBLICATION: json.dumps(publication)}})
        return self.digest(ref)


class DeliveryTests(unittest.TestCase):
    def test_prod_selects_digest_and_finalizes_only_after_success(self):
        repo, argo, registry, github = Mock(), Mock(), Mock(), Mock()
        repo.sha.return_value = "head"
        record = {
            "channel": "stable",
            "branch": "main",
            "chart_digest": "sha256:abc",
            "build_sha": "head",
            "chart_repository": "registry/chart",
            "app_version": "0.1.0",
        }
        application = {
            "spec": {
                "source": {"repoURL": "oci://registry/chart", "path": "."},
                "syncPolicy": {},
            },
            "status": {
                "sync": {"revision": "sha256:abc", "status": "Synced"},
                "health": {"status": "Healthy"},
                "operationState": {
                    "phase": "Succeeded",
                    "syncResult": {"revision": "sha256:abc"},
                },
            },
        }
        argo.get.return_value = application
        queued = copy.deepcopy(application)
        queued["operation"] = {"sync": {}}
        argo.get.side_effect = [queued, application, application]
        self.assertTrue(
            deliver(
                repo,
                record,
                github,
                enabled="true",
                registry=registry,
                argo=argo,
                run_id="123",
                attempt="2",
            )
        )
        argo.select.assert_called_once_with("sha256:abc", "prod-head-123-2")
        argo.sync.assert_called_once()
        argo.wait_operation.assert_called_once()
        registry.alias.assert_not_called()
        github.finalize.assert_called_once_with("v0.1.0")
        github.reset_mock()
        argo.get.side_effect = None
        application["status"]["operationState"]["phase"] = "Failed"
        with self.assertRaisesRegex(Error, "delivery failed"):
            deliver(
                repo,
                record,
                github,
                enabled="true",
                registry=registry,
                argo=argo,
                run_id="123",
                attempt="3",
            )
        github.finalize.assert_not_called()

    def test_disabled_delivery_has_no_calls_even_with_invalid_metadata(self):
        for enabled in ("", "false", "True", "1"):
            remote = Mock()
            self.assertFalse(
                deliver(
                    remote, {}, remote, enabled=enabled, registry=remote, argo=remote
                )
            )
            self.assertEqual(remote.mock_calls, [])

    def test_late_build_does_not_touch_registry_or_argo(self):
        repo, argo, registry = Mock(), Mock(), Mock()
        repo.sha.return_value = "newer"
        record = {
            "channel": "dev",
            "branch": "develop",
            "chart_digest": "sha256:abc",
            "build_sha": "old",
        }
        self.assertFalse(
            deliver(repo, record, Mock(), enabled="true", registry=registry, argo=argo)
        )
        self.assertEqual(argo.mock_calls, [])
        self.assertEqual(registry.mock_calls, [])

    def test_dev_moves_alias_and_waits_for_selected_digest(self):
        repo, argo, registry = Mock(), Mock(), Mock()
        repo.sha.return_value = "head"
        record = {
            "channel": "dev",
            "branch": "develop",
            "chart_digest": "sha256:abc",
            "build_sha": "head",
            "chart_repository": "registry/chart",
        }
        app = {
            "spec": {
                "source": {
                    "repoURL": "oci://registry/chart",
                    "path": ".",
                    "targetRevision": "dev",
                },
                "syncPolicy": {"automated": {"enabled": True}},
            },
            "status": {
                "sync": {"revision": "sha256:abc", "status": "Synced"},
                "health": {"status": "Healthy"},
                "operationState": {
                    "phase": "Succeeded",
                    "syncResult": {"revision": "sha256:abc"},
                },
            },
        }
        stale = copy.deepcopy(app)
        stale["status"]["sync"]["revision"] = "sha256:old"
        argo.get.side_effect = [app, app, stale, app]
        with mock_patch("scripts.cicd.delivery.time.sleep"):
            self.assertTrue(
                deliver(
                    repo, record, Mock(), enabled="true", registry=registry, argo=argo
                )
            )
        registry.alias.assert_called_once_with("registry/chart", "sha256:abc", "dev")
        argo.select.assert_not_called()

    def test_registry_auth_failure_is_not_treated_as_missing_version(self):
        with mock_patch(
            "scripts.cicd.artifacts.run",
            return_value=Mock(returncode=1, stderr="401 Unauthorized"),
        ):
            with self.assertRaisesRegex(Error, "Registry lookup failed"):
                Registry().manifest("registry/chart:0.1.0")

    def test_workflow_guards_every_delivery_step(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
        for step in workflow["jobs"]["deliver"]["steps"]:
            if step.get("name", "").startswith("Delivery remains disabled"):
                continue
            self.assertEqual(step.get("if"), "env.DEPLOY_ENABLED == 'true'")
        self.assertFalse(
            workflow["jobs"]["deliver"]["concurrency"]["cancel-in-progress"]
        )


if __name__ == "__main__":
    unittest.main()
