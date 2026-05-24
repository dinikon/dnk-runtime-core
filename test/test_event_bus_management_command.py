from __future__ import annotations

import argparse
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.management.cli import build_parser
from src.management.commands import events as events_command
from src.modules.shared.application.events import PublishOutboxResultDTO


class EventBusManagementCommandTests(unittest.IsolatedAsyncioTestCase):
    def test_parser_registers_publish_outbox_command(self) -> None:
        args = build_parser().parse_args(
            [
                "events",
                "publish-outbox",
                "--limit",
                "25",
                "--max-attempts",
                "7",
            ]
        )

        self.assertEqual(args.limit, 25)
        self.assertEqual(args.max_attempts, 7)
        self.assertIs(args.handler, events_command.handle_publish_outbox)

    async def test_handle_publish_outbox_prints_summary(self) -> None:
        stdout = io.StringIO()
        recorded_command = None

        class PublisherStub:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb) -> None:
                return None

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
                return PublishOutboxResultDTO(scanned=4, published=3, failed=1)

        def build_use_case_stub(**_kwargs):
            return UseCaseStub()

        args = argparse.Namespace(limit=10, max_attempts=5)

        with (
            patch.object(
                events_command,
                "build_integration_event_publisher",
                return_value=PublisherStub(),
            ),
            patch.object(events_command, "UnitOfWork", UnitOfWorkStub),
            patch.object(
                events_command,
                "build_publish_outbox_events_use_case",
                build_use_case_stub,
            ),
            redirect_stdout(stdout),
        ):
            exit_code = await events_command.handle_publish_outbox(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(recorded_command.limit, 10)
        self.assertEqual(recorded_command.max_attempts, 5)
        self.assertIn("OK scanned=4 published=3 failed=1", stdout.getvalue())


__all__ = ["EventBusManagementCommandTests"]
