"""Real local Git transactions, version reservations and crash recovery."""

import json
from pathlib import Path
from unittest.mock import patch as mock_patch

from scripts.cicd.common import Error
from scripts.cicd.common import versions, write_json
from scripts.cicd.gitops import prepare_rc, publish, release_sources, start_release
from scripts.cicd.formatting import format_python
from test.cicd.support import ReleaseRepoTestCase


class ReleaseTests(ReleaseRepoTestCase):
    def failed_publication(self) -> str:
        """Останавливает публикацию после создания локального стабильного тега."""
        start_release(self.repo)
        self.rc()
        with self.assertRaisesRegex(Error, "simulated"):
            publish(
                self.repo,
                self.github,
                lambda: (_ for _ in ()).throw(Error("simulated check failure")),
            )
        return self.repo.sha("v0.1.0")

    def test_rc_formats_python_in_version_commit_without_changing_source(self) -> None:
        """RC содержит форматирование, а исходный коммит и его ветка сохранены."""
        (self.root / "src").mkdir()
        source = self.commit(
            "feat: unformatted Python", "src/example.py", "value=  1\n"
        )
        self.repo.git("push", "origin", "develop")
        start_release(self.repo)
        tag = self.rc()
        self.assertEqual(self.repo.sha(), source)
        self.assertEqual(self.repo.sha(tag + "^"), source)
        self.assertEqual((self.root / "src/example.py").read_text(), "value=  1\n")
        with self.repo.checkout(tag) as checkout:
            self.assertEqual(
                (checkout.root / "src/example.py").read_text(), "value = 1\n"
            )
            format_python(checkout.root, check=True)
            checkout.clean()

    def test_hotfix_formats_python_before_stable_validation(self) -> None:
        """Исправление стиля включается в стабильную версию до запуска проверок."""
        self.initial_release()
        self.repo.git("switch", "-c", "hotfix/formatting", "main")
        (self.root / "test").mkdir()
        self.commit("fix: unformatted Python", "test/example.py", "value=  1\n")
        publish(self.repo, self.github, lambda: format_python(self.root, check=True))
        self.assertEqual(self.repo.sha("v0.1.1"), self.repo.sha("origin/main"))
        self.assertEqual((self.root / "test/example.py").read_text(), "value = 1\n")
        self.repo.clean()

    def test_invalid_python_stops_before_rc_version_or_tag_creation(self) -> None:
        """Ошибка Black не создаёт неполную RC-версию."""
        (self.root / "src").mkdir()
        source = self.commit("feat: invalid Python", "src/example.py", "def broken(:\n")
        self.repo.git("push", "origin", "develop")
        start_release(self.repo)
        with self.assertRaises(Error):
            prepare_rc(self.repo, self.repo.branch(), source)
        self.assertFalse(self.repo.exists("refs/tags/v0.1.0-rc.1"))
        self.assertEqual(self.repo.sha(), source)
        self.assertEqual(versions(self.root), ("0.1.0", "0.3.2"))
        self.repo.clean()

    def test_check_retry_accepts_fix_commit_and_revalidates_before_retag(self) -> None:
        """Повторная неудача сохраняет старый тег; успех публикует проверенную правку."""
        original = self.failed_publication()
        candidate = self.repo.sha("v0.1.0-rc.1")
        source = self.repo.metadata("v0.1.0")["source_sha"]
        corrected = self.commit("style: fix formatting", "fixed.py", "value = 1\n")
        with self.assertRaisesRegex(Error, "still failing"):
            publish(
                self.repo,
                self.github,
                lambda: (_ for _ in ()).throw(Error("still failing")),
            )
        self.assertEqual(self.repo.sha("v0.1.0"), original)

        def check() -> None:
            """Проверяет исправляющий коммит до переноса тега и отправки ссылок."""
            self.assertEqual(self.repo.sha(), corrected)
            self.assertEqual(self.repo.sha("v0.1.0"), original)
            self.assertNotEqual(self.repo.sha("origin/main"), corrected)

        publish(self.repo, self.github, check)
        self.assertEqual(self.repo.sha("origin/main"), corrected)
        self.assertEqual(self.repo.sha("v0.1.0"), corrected)
        self.assertEqual(self.repo.sha("v0.1.0-rc.1"), candidate)
        self.assertEqual(self.repo.metadata("v0.1.0")["source_sha"], source)
        self.assertEqual(versions(self.root), ("0.1.0", "0.3.3"))

    def test_check_retry_does_not_move_published_tag(self) -> None:
        """Даже отдельная отправка стабильного тега запрещает его перенос."""
        original = self.failed_publication()
        self.repo.git("push", "origin", "refs/tags/v0.1.0")
        self.commit("fix: correction after check")
        with self.assertRaisesRegex(Error, "already on origin"):
            publish(self.repo, self.github, lambda: self.fail("Must not run checks"))
        self.assertEqual(self.repo.sha("v0.1.0"), original)

    def test_check_retry_rejects_version_changes_and_rewritten_main(self) -> None:
        """Повтор принимает только продолжение подготовленной истории с той же версией."""
        original = self.failed_publication()
        self.commit(
            "fix: wrong chart", "helm/Chart.yaml", "version: 9.9.9\nappVersion: 0.1.0\n"
        )
        with self.assertRaisesRegex(Error, "incompatibly"):
            publish(self.repo, self.github, lambda: self.fail("Must not run checks"))
        self.repo.git("reset", "--hard", original + "^")
        self.commit("fix: rewritten main")
        with self.assertRaisesRegex(Error, "incompatibly"):
            publish(self.repo, self.github, lambda: self.fail("Must not run checks"))
        self.assertEqual(self.repo.sha("v0.1.0"), original)

    def test_retag_retry_recovers_interruption_after_tag_update(self) -> None:
        """Прерванная запись журнала после переноса тега безопасно повторяется."""
        self.failed_publication()
        corrected = self.commit("fix: local correction")
        journal = self.root / ".git/cicd-publish.json"

        def interrupt(path: Path, state: dict[str, object]) -> None:
            """Имитирует остановку после тега до сохранения следующей фазы."""
            if state["phase"] == "backmerge":
                raise OSError("simulated journal failure")
            write_json(path, state)

        with mock_patch("scripts.cicd.gitops.write_json", side_effect=interrupt):
            with self.assertRaisesRegex(OSError, "journal failure"):
                publish(self.repo, self.github, lambda: None)
        self.assertEqual(json.loads(journal.read_text())["phase"], "retag")
        self.assertEqual(self.repo.sha("v0.1.0"), corrected)
        publish(self.repo, self.github, lambda: self.fail("Already validated"))
        self.assertEqual(self.repo.sha("origin/main"), corrected)
        self.assertFalse(journal.exists())

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
