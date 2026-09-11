"""Real local Git transactions, version reservations and crash recovery."""

from unittest.mock import patch as mock_patch

from scripts.cicd.common import Error
from scripts.cicd.common import versions
from scripts.cicd.gitops import prepare_rc, publish, release_sources, start_release
from test.cicd.support import ReleaseRepoTestCase


class ReleaseTests(ReleaseRepoTestCase):
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
