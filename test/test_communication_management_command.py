from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from src.management.cli import build_parser
from src.management.commands import communication as communication_command
from src.modules.communication.application.dto import (
    ProcessQueuedResultDTO,
    PublishQueuedResultDTO,
    RecoverStuckResultDTO,
)
from src.modules.communication.domain import CommunicationValidationError


class CommunicationManagementCommandTests(unittest.IsolatedAsyncioTestCase):
    def test_parser_registers_process_queued_command(self) -> None:
        args = build_parser().parse_args(
            ["communication", "process-queued", "--limit", "25"]
        )

        self.assertEqual(args.limit, 25)
        self.assertIs(args.handler, communication_command.handle_process_queued)

    def test_parser_registers_queue_commands(self) -> None:
        publish_args = build_parser().parse_args(
            ["communication", "publish-queued", "--limit", "25"]
        )
        recover_args = build_parser().parse_args(
            [
                "communication",
                "recover-stuck",
                "--older-than-seconds",
                "600",
                "--limit",
                "5",
            ]
        )
        worker_args = build_parser().parse_args(["communication", "worker"])

        self.assertEqual(publish_args.limit, 25)
        self.assertIs(publish_args.handler, communication_command.handle_publish_queued)
        self.assertEqual(recover_args.older_than_seconds, 600)
        self.assertEqual(recover_args.limit, 5)
        self.assertIs(recover_args.handler, communication_command.handle_recover_stuck)
        self.assertIs(worker_args.handler, communication_command.handle_worker)

    async def test_handle_process_queued_prints_summary(self) -> None:
        stdout = io.StringIO()
        recorded_limit = None

        class UseCaseStub:
            async def __call__(self, command):
                nonlocal recorded_limit
                recorded_limit = command.limit
                return ProcessQueuedResultDTO(processed=3, succeeded=2, failed=1)

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        args = argparse.Namespace(limit=10)

        with (
            patch.object(
                communication_command,
                "build_process_outbound_message_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(communication_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stdout(stdout),
        ):
            exit_code = await communication_command.handle_process_queued(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_limit, 10)
        self.assertIn("OK processed=3 succeeded=2 failed=1", stdout.getvalue())

    async def test_handle_process_queued_returns_2_for_communication_error(
        self,
    ) -> None:
        stderr = io.StringIO()

        class UseCaseStub:
            async def __call__(self, _command):
                raise CommunicationValidationError("bad provider payload")

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        args = argparse.Namespace(limit=10)

        with (
            patch.object(
                communication_command,
                "build_process_outbound_message_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(communication_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stderr(stderr),
        ):
            exit_code = await communication_command.handle_process_queued(args)

        self.assertEqual(exit_code, 2)
        self.assertEqual(stderr.getvalue().strip(), "bad provider payload")

    async def test_handle_publish_queued_prints_summary(self) -> None:
        stdout = io.StringIO()
        recorded_limit = None

        class PublisherStub:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        class UseCaseStub:
            async def __call__(self, command):
                nonlocal recorded_limit
                recorded_limit = command.limit
                return PublishQueuedResultDTO(scanned=3, published=2, failed=1)

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        args = argparse.Namespace(limit=10)

        with (
            patch.object(
                communication_command.RabbitMQOutboundMessagePublisher,
                "from_settings",
                return_value=PublisherStub(),
            ),
            patch.object(
                communication_command,
                "build_publish_queued_outbound_messages_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(communication_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stdout(stdout),
        ):
            exit_code = await communication_command.handle_publish_queued(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_limit, 10)
        self.assertIn("OK scanned=3 published=2 failed=1", stdout.getvalue())

    async def test_handle_recover_stuck_prints_summary(self) -> None:
        stdout = io.StringIO()
        recorded_seconds = None

        class UseCaseStub:
            async def __call__(self, command):
                nonlocal recorded_seconds
                recorded_seconds = command.older_than_seconds
                return RecoverStuckResultDTO(recovered=4)

        class UnitOfWorkStub:
            def __init__(self, _session_factory):
                self.session = object()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

        args = argparse.Namespace(older_than_seconds=600, limit=5)

        with (
            patch.object(
                communication_command,
                "build_recover_stuck_outbound_messages_use_case",
                return_value=UseCaseStub(),
            ),
            patch.object(communication_command, "UnitOfWork", UnitOfWorkStub),
            redirect_stdout(stdout),
        ):
            exit_code = await communication_command.handle_recover_stuck(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_seconds, 600)
        self.assertIn("OK recovered=4", stdout.getvalue())


__all__ = ["CommunicationManagementCommandTests"]
