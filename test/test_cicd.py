"""Release transactions use real Git/Commitizen, temporary repos and fake remote APIs."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch as mock_patch

import httpx
import tomlkit
import yaml

from scripts.cicd.artifacts import (
    GitHub,
    PUBLICATION,
    Registry,
    package_chart,
    publish_artifacts,
    publish_images,
    publish_channel_aliases,
    wait_for_manifest,
)
from scripts.cicd.common import Error, ROOT, run, versions
from scripts.cicd.__main__ import ci
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


class GitHubReleaseTests(unittest.TestCase):
    def setUp(self):
        self.github = GitHub("owner/repo")
        self.requests = []
        self.responses = []
        self.release = {
            "draft": False,
            "prerelease": True,
            "tag_name": "v0.1.0-rc.1",
            "body": "Release notes",
        }
        self.enterContext(mock_patch.dict(os.environ, {}, clear=True))
        self.enterContext(
            mock_patch(
                "scripts.cicd.artifacts.run",
                side_effect=AssertionError("Release lookup must not call gh"),
            )
        )
        client = httpx.Client
        self.enterContext(
            mock_patch(
                "scripts.cicd.artifacts.httpx.Client",
                side_effect=lambda **kwargs: client(
                    transport=httpx.MockTransport(self.respond), **kwargs
                ),
            )
        )

    def respond(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def test_public_release_without_token_or_gh(self):
        self.responses.append(httpx.Response(200, json=self.release))
        self.assertEqual(
            self.github.get_release("v0.1.0-rc.1"),
            {
                "isDraft": False,
                "isPrerelease": True,
                "tagName": "v0.1.0-rc.1",
                "body": "Release notes",
            },
        )
        request = self.requests[0]
        self.assertEqual(
            str(request.url),
            "https://api.github.com/repos/owner/repo/releases/tags/v0.1.0-rc.1",
        )
        self.assertNotIn("Authorization", request.headers)

    def test_environment_tokens_and_precedence(self):
        for environment, token in (
            ({"GH_TOKEN": "gh-token"}, "gh-token"),
            ({"GITHUB_TOKEN": "github-token"}, "github-token"),
            ({"GH_TOKEN": "gh-token", "GITHUB_TOKEN": "github-token"}, "gh-token"),
            ({"GH_TOKEN": "", "GITHUB_TOKEN": "github-token"}, "github-token"),
        ):
            with (
                self.subTest(environment=environment),
                mock_patch.dict(os.environ, environment, clear=True),
            ):
                self.responses.append(httpx.Response(200, json=self.release))
                self.github.get_release("v0.1.0-rc.1")
                self.assertEqual(
                    self.requests[-1].headers["Authorization"], "Bearer " + token
                )

    def test_missing_release_returns_none_when_releases_are_accessible(self):
        self.responses.extend(
            [httpx.Response(404), httpx.Response(200, json=[self.release])]
        )
        self.assertIsNone(self.github.get_release("v0.1.0-rc.2"))

    def test_draft_release_is_found_on_later_page(self):
        os.environ["GH_TOKEN"] = "test-token"
        draft = self.release | {
            "tag_name": "v0.1.0",
            "draft": True,
            "prerelease": False,
        }
        self.responses.extend(
            [
                httpx.Response(404),
                httpx.Response(
                    200,
                    json=[self.release],
                    headers={
                        "Link": '<https://api.github.com/repos/owner/repo/releases?page=2>; rel="next"'
                    },
                ),
                httpx.Response(200, json=[draft]),
            ]
        )
        result = self.github.get_release("v0.1.0")
        self.assertTrue(result["isDraft"])
        self.assertFalse(result["isPrerelease"])
        self.assertEqual(self.requests[-1].url.params["page"], "2")
        self.assertEqual(
            self.requests[-1].headers["Authorization"], "Bearer test-token"
        )

    def test_inaccessible_repository_is_not_treated_as_pending_release(self):
        self.responses.extend([httpx.Response(404), httpx.Response(404)])
        with self.assertRaisesRegex(Error, "HTTP 404.*GH_TOKEN"):
            self.github.get_release("v0.1.0-rc.1")

    def test_api_failures_are_actionable_without_exposing_token(self):
        os.environ["GH_TOKEN"] = "secret-token"
        for status in (401, 403, 429, 500):
            with self.subTest(status=status):
                self.responses.append(httpx.Response(status, text="secret-token"))
                with self.assertRaisesRegex(Error, f"HTTP {status}.*GH_TOKEN") as error:
                    self.github.get_release("v0.1.0-rc.1")
                self.assertNotIn("secret-token", str(error.exception))

    def test_network_failures_are_actionable(self):
        for failure in (httpx.ConnectError, httpx.ReadTimeout):
            with self.subTest(failure=failure):
                self.responses.append(failure("Connection failed"))
                with self.assertRaisesRegex(Error, "check the network connection"):
                    self.github.get_release("v0.1.0-rc.1")


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock_patch("scripts.cicd.artifacts.time.sleep"))
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
        # Start from an unreleased fixture, even when checks run on an RC/stable
        # checkout. Copying its versions would change every expected release.
        project_path = self.root / "pyproject.toml"
        project = tomlkit.parse(project_path.read_text())
        project["project"]["version"] = "0.1.0"
        project_path.write_text(tomlkit.dumps(project))
        lock_path = self.root / "uv.lock"
        lock = tomlkit.parse(lock_path.read_text())
        for package in lock["package"]:
            if package["name"] == project["project"]["name"]:
                package["version"] = "0.1.0"
                break
        else:
            self.fail("Application package is missing from the fixture lockfile")
        lock_path.write_text(tomlkit.dumps(lock))
        chart_path = self.root / "helm/Chart.yaml"
        chart = yaml.safe_load(chart_path.read_text())
        chart.update(version="0.3.2", appVersion="0.1.0")
        chart_path.write_text(yaml.safe_dump(chart, sort_keys=False))
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

    def test_ci_stable_release_precedes_aliases_and_needs_only_ready_artifacts(self):
        self.initial_release()
        head = self.repo.sha("v0.1.0")
        record = {"channel": "stable", "branch": "main", "build_sha": head}
        github = Mock()
        events = Mock()
        events.attach_mock(github.publish, "release")
        with (
            mock_patch.dict(
                os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}
            ),
            mock_patch(
                "scripts.cicd.__main__.publish_artifacts", return_value=record
            ) as artifacts,
            mock_patch("scripts.cicd.__main__.publish_channel_aliases") as aliases,
        ):
            events.attach_mock(aliases, "aliases")
            ci(self.repo, github, "main", head, self.root / "publication.json")
            self.assertEqual(
                [call[0] for call in events.mock_calls], ["release", "aliases"]
            )
            self.assertTrue(github.publish.call_args.kwargs["latest"])
            self.assertEqual(github.publish.call_args.args[0], "v0.1.0")
            github.reset_mock()
            aliases.reset_mock()
            artifacts.side_effect = Error("image publication failed")
            with self.assertRaisesRegex(Error, "image publication failed"):
                ci(self.repo, github, "main", head, self.root / "publication.json")
            github.publish.assert_not_called()
            aliases.assert_not_called()


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


class ArtifactTests(unittest.TestCase):
    prefix = "registry.example/runtime"
    app = "0.1.0-rc.1"
    source = "12345678" + "a" * 32

    def setUp(self):
        self.sleep = self.enterContext(mock_patch("scripts.cicd.artifacts.time.sleep"))

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
            "scripts.cicd.artifacts.run",
            return_value=Mock(returncode=1, stderr="401 Unauthorized"),
        ):
            with self.assertRaisesRegex(
                Error, "Registry lookup failed for registry/chart:0.1.0"
            ):
                Registry().manifest("registry/chart:0.1.0")


class GitHubPublicationTests(unittest.TestCase):
    def setUp(self):
        self.github = GitHub("owner/repo")
        self.lookup = self.enterContext(
            mock_patch.object(self.github, "get_release", return_value=None)
        )
        self.run = self.enterContext(mock_patch("scripts.cicd.artifacts.run"))

    def test_stable_release_is_created_published_and_latest(self):
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes", latest=True)
        args = self.run.call_args.args
        self.assertEqual(args[:4], ("gh", "release", "create", "v0.1.0"))
        self.assertIn("--verify-tag", args)
        self.assertIn("--draft=false", args)
        self.assertIn("--latest", args)
        self.assertNotIn("--prerelease", args)

    def test_rc_is_published_prerelease_and_never_latest(self):
        self.github.publish("v0.1.0-rc.1", {"channel": "rc"}, "Changes", latest=True)
        args = self.run.call_args.args
        self.assertIn("--draft=false", args)
        self.assertIn("--prerelease", args)
        self.assertIn("--latest=false", args)

    def test_retry_publishes_existing_stable_draft(self):
        self.lookup.return_value = {"isDraft": True, "isPrerelease": False}
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes", latest=True)
        args = self.run.call_args.args
        self.assertEqual(args[:4], ("gh", "release", "edit", "v0.1.0"))
        self.assertIn("--draft=false", args)
        self.assertIn("--latest", args)

    def test_old_stable_retry_does_not_become_latest(self):
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes", latest=False)
        self.assertIn("--latest=false", self.run.call_args.args)

    def test_published_release_is_not_rewritten(self):
        self.lookup.return_value = {"isDraft": False, "isPrerelease": False}
        self.github.publish("v0.1.0", {"channel": "stable"}, "Changes")
        self.run.assert_not_called()


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
        self.enterContext(mock_patch("scripts.cicd.artifacts.time.sleep"))

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


class WorkflowTests(unittest.TestCase):
    def test_workflow_only_publishes_without_deployment_environment(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
        self.assertEqual(set(workflow["jobs"]), {"publish"})
        job = workflow["jobs"]["publish"]
        self.assertNotIn("environment", job)
        self.assertNotIn("deployments", workflow["permissions"])
        commands = "\n".join(step.get("run", "") for step in job["steps"])
        self.assertNotIn("argocd", commands.lower())
        self.assertNotIn("kubectl", commands.lower())
        self.assertNotIn("scripts.cicd deliver", commands)
        self.assertFalse(job["concurrency"]["cancel-in-progress"])

    def test_failed_artifact_publication_does_not_publish_release_or_aliases(self):
        github = Mock()
        with (
            mock_patch.dict(
                os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}
            ),
            mock_patch(
                "scripts.cicd.__main__.publish_artifacts",
                side_effect=Error("build failed"),
            ),
            mock_patch("scripts.cicd.__main__.publish_channel_aliases") as aliases,
        ):
            with self.assertRaisesRegex(Error, "build failed"):
                ci(Mock(), github, "develop", "head", Path("unused.json"))
        github.publish.assert_not_called()
        aliases.assert_not_called()


if __name__ == "__main__":
    unittest.main()
