"""Workflow permissions and publication ordering."""

from pathlib import Path
from unittest.mock import Mock, patch as mock_patch
import json
import os
import tempfile
import unittest

import yaml

from scripts.cicd.common import Error, ROOT
from scripts.cicd.pipeline import ci
from test.cicd.support import ReleaseRepoTestCase


class StablePipelineTests(ReleaseRepoTestCase):
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
                "scripts.cicd.pipeline.publish_artifacts", return_value=record
            ) as artifacts,
            mock_patch("scripts.cicd.pipeline.publish_channel_aliases") as aliases,
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

    def test_failure_diagnostics_are_saved_for_every_branch_and_attempt(self):
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
        steps = workflow["jobs"]["publish"]["steps"]
        upload = next(
            step
            for step in steps
            if step.get("uses", "").startswith("actions/upload-artifact@")
        )
        self.assertEqual(upload["if"], "always()")
        self.assertIn("github.run_attempt", upload["with"]["name"])
        self.assertIn("publications/*.json", upload["with"]["path"])
        self.assertIn("publication.log", upload["with"]["path"])
        publisher = next(
            step for step in steps if "scripts.cicd ci" in step.get("run", "")
        )
        self.assertEqual(publisher["shell"], "bash")
        self.assertIn("pipefail", publisher["run"])

    def test_failed_artifact_publication_does_not_publish_release_or_aliases(self):
        github = Mock()
        with (
            mock_patch.dict(
                os.environ, {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}
            ),
            mock_patch(
                "scripts.cicd.pipeline.publish_artifacts",
                side_effect=Error("build failed"),
            ),
            mock_patch("scripts.cicd.pipeline.publish_channel_aliases") as aliases,
        ):
            with self.assertRaisesRegex(Error, "build failed"):
                ci(Mock(), github, "develop", "head", Path("unused.json"))
        github.publish.assert_not_called()
        aliases.assert_not_called()


class ReleasePipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.output = Path(self.directory) / "publication.json"
        self.repo = Mock()
        self.repo.exists.return_value = False
        self.repo.git.return_value.stdout = "Changelog"
        self.github = Mock()
        self.enterContext(
            mock_patch.dict(
                os.environ,
                {
                    "GITHUB_RUN_ID": "123",
                    "GITHUB_RUN_ATTEMPT": "2",
                },
            )
        )
        self.enterContext(
            mock_patch(
                "scripts.cicd.pipeline.release_sources",
                return_value=["first", "second"],
            )
        )
        self.prepare = self.enterContext(
            mock_patch(
                "scripts.cicd.pipeline.prepare_rc",
                side_effect=["v0.2.0-rc.1", "v0.2.0-rc.2"],
            )
        )
        self.records = [
            {"source_sha": source, "channel": "rc"} for source in ("first", "second")
        ]
        self.artifacts = self.enterContext(
            mock_patch(
                "scripts.cicd.pipeline.publish_artifacts", side_effect=self.records
            )
        )
        self.aliases = self.enterContext(
            mock_patch("scripts.cicd.pipeline.publish_channel_aliases")
        )

    def publish(self):
        ci(self.repo, self.github, "release/0.2.0", "second", self.output)

    def test_each_rc_record_is_kept_and_latest_record_is_compatible(self):
        self.publish()
        self.assertEqual(json.loads(self.output.read_text()), self.records[-1])
        for number, record in enumerate(self.records, 1):
            path = self.output.parent / "publications" / f"v0.2.0-rc.{number}.json"
            self.assertEqual(json.loads(path.read_text()), record)
        self.assertEqual(
            [call.args[0] for call in self.github.publish.call_args_list],
            ["v0.2.0-rc.1", "v0.2.0-rc.2"],
        )
        self.aliases.assert_not_called()

    def test_second_artifact_failure_retains_first_record_and_stops_releases(self):
        self.artifacts.side_effect = [self.records[0], Error("second build failed")]
        with self.assertRaisesRegex(Error, "second build failed"):
            self.publish()
        self.assertEqual(json.loads(self.output.read_text()), self.records[0])
        self.assertEqual(
            len(list((self.output.parent / "publications").glob("*.json"))), 1
        )
        self.github.publish.assert_called_once()
        self.aliases.assert_not_called()

    def test_github_failure_keeps_ready_artifacts_and_stops_next_candidate(self):
        self.github.publish.side_effect = Error("GitHub unavailable")
        with self.assertRaisesRegex(Error, "GitHub unavailable"):
            self.publish()
        self.assertEqual(json.loads(self.output.read_text()), self.records[0])
        self.assertTrue(
            (self.output.parent / "publications/v0.2.0-rc.1.json").is_file()
        )
        self.prepare.assert_called_once()
        self.aliases.assert_not_called()

    def test_finalized_release_skips_candidates_and_records(self):
        self.repo.exists.return_value = True
        self.publish()
        self.prepare.assert_not_called()
        self.artifacts.assert_not_called()
        self.github.publish.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_invalid_run_identity_stops_before_fetch_or_publication(self):
        with mock_patch.dict(os.environ, {"GITHUB_RUN_ID": "invalid"}):
            with self.assertRaisesRegex(Error, "must be numeric"):
                self.publish()
        self.repo.fetch.assert_not_called()
        self.artifacts.assert_not_called()
