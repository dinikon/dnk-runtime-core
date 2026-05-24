from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.management.cli import build_parser
from src.management.commands import jobs as jobs_command
from src.modules.shared.application.jobs import (
    ProcessDueScheduledJobsResultDTO,
    RecoverStuckJobsResultDTO,
)


class JobsManagementCommandTests(unittest.IsolatedAsyncioTestCase):
    def test_parser_registers_process_due_command(self) -> None:
        args = build_parser().parse_args(
            [
                "jobs",
                "process-due",
                "--limit",
                "25",
                "--max-attempts",
                "7",
                "--lock-ttl-seconds",
                "120",
            ]
        )

        self.assertEqual(args.limit, 25)
        self.assertEqual(args.max_attempts, 7)
        self.assertEqual(args.lock_ttl_seconds, 120)
        self.assertIs(args.handler, jobs_command.handle_process_due)

    def test_parser_registers_recover_stuck_command(self) -> None:
        args = build_parser().parse_args(
            [
                "jobs",
                "recover-stuck",
                "--limit",
                "12",
                "--max-attempts",
                "4",
            ]
        )

        self.assertEqual(args.limit, 12)
        self.assertEqual(args.max_attempts, 4)
        self.assertIs(args.handler, jobs_command.handle_recover_stuck)

    async def test_handle_process_due_prints_summary(self) -> None:
        stdout = io.StringIO()
        recorded_command = None

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        class UseCaseStub:
            async def __call__(self, command):
                nonlocal recorded_command
                recorded_command = command
                return ProcessDueScheduledJobsResultDTO(
                    scanned=4,
                    processed=4,
                    done=3,
                    failed=1,
                    retried=1,
                )

        def build_use_case_stub(**_kwargs):
            return UseCaseStub()

        args = argparse.Namespace(
            limit=10,
            max_attempts=5,
            lock_ttl_seconds=300,
        )

        with (
            patch.object(jobs_command, "UnitOfWork", UnitOfWorkStub),
            patch.object(
                jobs_command,
                "build_process_due_scheduled_jobs_use_case",
                build_use_case_stub,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = await jobs_command.handle_process_due(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_command.limit, 10)
        self.assertEqual(recorded_command.max_attempts, 5)
        self.assertEqual(recorded_command.lock_ttl_seconds, 300)
        self.assertIn(
            "OK scanned=4 processed=4 done=3 failed=1 retried=1",
            stdout.getvalue(),
        )

    async def test_handle_recover_stuck_prints_summary(self) -> None:
        stdout = io.StringIO()
        recorded_command = None

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        class UseCaseStub:
            async def __call__(self, command):
                nonlocal recorded_command
                recorded_command = command
                return RecoverStuckJobsResultDTO(scanned=3, recovered=2, failed=1)

        def build_use_case_stub(**_kwargs):
            return UseCaseStub()

        args = argparse.Namespace(limit=10, max_attempts=5)

        with (
            patch.object(jobs_command, "UnitOfWork", UnitOfWorkStub),
            patch.object(
                jobs_command,
                "build_recover_stuck_scheduled_jobs_use_case",
                build_use_case_stub,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = await jobs_command.handle_recover_stuck(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_command.limit, 10)
        self.assertEqual(recorded_command.max_attempts, 5)
        self.assertIn("OK scanned=3 recovered=2 failed=1", stdout.getvalue())


__all__ = ["JobsManagementCommandTests"]
