"""Logging must preserve failure semantics, context boundaries and secret isolation."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch
import logging
import os
import tempfile
import unittest

from scripts.cicd.common import Error, live, run
from scripts.cicd.observability import (
    ContextFormatter,
    configure_logging,
    log_context,
    logger,
    stage,
)


class ObservabilityTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {}, clear=True))
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.summary = Path(self.directory) / "summary.md"
        self.enterContext(
            patch.dict(
                os.environ,
                {
                    "GITHUB_ACTIONS": "true",
                    "GITHUB_STEP_SUMMARY": str(self.summary),
                },
            )
        )
        self.output = self.enterContext(redirect_stdout(StringIO()))
        self.logs = StringIO()
        self.enterContext(patch("sys.stderr", self.logs))
        original = logger.handlers[:], logger.level, logger.propagate
        self.addCleanup(self.restore_logger, *original)
        configure_logging("DEBUG")

    @staticmethod
    def restore_logger(handlers, level, propagate):
        logger.handlers[:] = handlers
        logger.setLevel(level)
        logger.propagate = propagate

    def test_nested_failure_preserves_exception_and_closes_one_actions_group(self):
        error = Error("original failure")
        with self.assertRaises(Error) as raised:
            with log_context(branch="release/0.2.0", sha="abc123", attempt="2"):
                with stage("Publish"):
                    with stage("Build"):
                        raise error
        self.assertIs(raised.exception, error)
        output = self.output.getvalue()
        self.assertEqual(output.count("::group::"), 1)
        self.assertEqual(output.count("::endgroup::"), 1)
        self.assertEqual(output.count("::error::"), 1)
        self.assertEqual(self.summary.read_text().count("| failed |"), 2)
        self.assertIn('branch="release/0.2.0"', self.logs.getvalue())
        logger.info("Outside the operation")
        self.assertNotIn("branch=", self.logs.getvalue().splitlines()[-1])
        self.assertNotIn("stage=", self.logs.getvalue().splitlines()[-1])

    def test_success_records_elapsed_time_and_escapes_actions_and_markdown(self):
        with patch("scripts.cicd.observability.time.monotonic", side_effect=[10, 12.5]):
            with stage("Build\n::error::injected|<tag>100%"):
                pass
        self.assertIn("| success | 2.50 |", self.summary.read_text())
        self.assertIn("&#124;&lt;tag&gt;", self.summary.read_text())
        self.assertIn("Build%0A::error::injected|<tag>100%25", self.output.getvalue())
        self.assertNotIn("\n::error::", self.output.getvalue())

    def test_local_logs_have_no_actions_control_lines(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with stage("Local check"):
                logger.info("Still visible")
        self.assertEqual(self.output.getvalue(), "")
        self.assertIn("Still visible", self.logs.getvalue())

    def test_summary_write_failure_never_replaces_publication_error(self):
        with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": self.directory}):
            with self.assertRaisesRegex(Error, "original"):
                with stage("Publish"):
                    raise Error("original")
        self.assertIn("Could not append the job summary", self.logs.getvalue())

    def test_process_logs_exclude_arguments_and_environment_values(self):
        result = Mock(returncode=0, stdout="", stderr="")
        with patch("scripts.cicd.common.subprocess.run", return_value=result):
            run(
                "oras",
                "login",
                "--password",
                "argument-secret",
                env={"GH_TOKEN": "env-secret"},
            )
            live(
                "docker",
                "login",
                "--password",
                "argument-secret",
                env={"GH_TOKEN": "env-secret"},
            )
        logs = self.logs.getvalue()
        self.assertIn("duration=", logs)
        self.assertNotIn("argument-secret", logs)
        self.assertNotIn("env-secret", logs)
        self.assertNotIn("--password", logs)

    def test_process_failure_is_not_swallowed(self):
        with patch(
            "scripts.cicd.common.subprocess.run", return_value=Mock(returncode=7)
        ):
            with self.assertRaisesRegex(Error, "failed \\(7\\)"):
                live("docker", "buildx", "bake")

    def test_configuration_is_idempotent_and_leaves_root_logger_alone(self):
        handlers = logging.getLogger().handlers[:]
        configure_logging()
        configure_logging()
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0].formatter, ContextFormatter)
        self.assertEqual(logging.getLogger().handlers, handlers)
