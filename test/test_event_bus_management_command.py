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

    def test_parser_registers_publisher_worker_command(self) -> None:
        args = build_parser().parse_args(["events", "publisher-worker"])

        self.assertIs(args.handler, events_command.handle_publisher_worker)

    def test_parser_registers_console_worker_command(self) -> None:
        args = build_parser().parse_args(["events", "console-worker"])

        self.assertEqual(args.queue_name, "crm.contact.events")
        self.assertEqual(args.routing_key, "crm.contact.#")
        self.assertIs(args.handler, events_command.handle_console_worker)

    def test_parser_registers_console_worker_custom_topology(self) -> None:
        args = build_parser().parse_args(
            [
                "events",
                "console-worker",
                "--queue-name",
                "analytics.events",
                "--routing-key",
                "analytics.#",
            ]
        )

        self.assertEqual(args.queue_name, "analytics.events")
        self.assertEqual(args.routing_key, "analytics.#")
        self.assertIs(args.handler, events_command.handle_console_worker)

    async def test_handle_publish_outbox_prints_summary(self) -> None:
        stdout = io.StringIO()
        recorded_command = None

        class ProviderStub:
            def __init__(self) -> None:
                self.started = False
                self.closed = False

            async def start(self) -> None:
                self.started = True

            async def close(self) -> None:
                self.closed = True

        class PublisherStub:
            pass

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

        async def ensure_topology_stub(*_args, **_kwargs):
            return None

        args = argparse.Namespace(limit=10, max_attempts=5)
        provider = ProviderStub()

        with (
            patch.object(
                events_command,
                "build_rabbitmq_event_publisher_for_cli",
                return_value=(provider, PublisherStub()),
            ),
            patch.object(
                events_command, "ensure_event_bus_topology", ensure_topology_stub
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
        self.assertTrue(provider.started)
        self.assertTrue(provider.closed)
        self.assertEqual(recorded_command.limit, 10)
        self.assertEqual(recorded_command.max_attempts, 5)
        self.assertIn("OK scanned=4 published=3 failed=1", stdout.getvalue())

    async def test_handle_publisher_worker_runs_and_closes_provider(self) -> None:
        recorded = {}

        class ProviderStub:
            def __init__(self, settings) -> None:
                recorded["rabbitmq_settings"] = settings
                self.started = False
                self.closed = False

            async def start(self) -> None:
                self.started = True

            async def close(self) -> None:
                self.closed = True

        class TopologyStub:
            def __init__(self, provider) -> None:
                recorded["topology"] = self
                recorded["topology_provider"] = provider

        class WorkerStub:
            def __init__(
                self,
                *,
                publish_once,
                idle_sleep_seconds,
                error_sleep_seconds,
            ) -> None:
                recorded["publish_once"] = publish_once
                recorded["idle_sleep_seconds"] = idle_sleep_seconds
                recorded["error_sleep_seconds"] = error_sleep_seconds
                self.ran = False

            async def run_forever(self) -> None:
                self.ran = True
                recorded["worker_ran"] = True

        async def ensure_topology_stub(*, topology, settings) -> None:
            recorded["ensure_topology"] = (topology, settings)

        async def publish_once_stub() -> PublishOutboxResultDTO:
            return PublishOutboxResultDTO(scanned=0, published=0, failed=0)

        def build_publish_once_stub(**kwargs):
            recorded["build_publish_once_kwargs"] = kwargs
            return publish_once_stub

        args = argparse.Namespace()
        provider_holder = {}

        def provider_factory(settings):
            provider = ProviderStub(settings)
            provider_holder["provider"] = provider
            return provider

        with (
            patch.object(
                events_command,
                "RabbitMQBrokerProvider",
                provider_factory,
            ),
            patch.object(
                events_command,
                "RabbitMQTopologyManager",
                TopologyStub,
            ),
            patch.object(
                events_command,
                "ensure_event_bus_topology",
                ensure_topology_stub,
            ),
            patch.object(
                events_command,
                "build_publish_once",
                build_publish_once_stub,
            ),
            patch.object(events_command, "OutboxPublisherWorker", WorkerStub),
            patch.object(events_command, "_configure_worker_logging"),
            patch.object(events_command, "_install_worker_signal_handlers"),
        ):
            exit_code = await events_command.handle_publisher_worker(args)

        provider = provider_holder["provider"]
        self.assertEqual(exit_code, 0)
        self.assertTrue(provider.started)
        self.assertTrue(provider.closed)
        self.assertIs(recorded["topology_provider"], provider)
        self.assertIs(recorded["ensure_topology"][0], recorded["topology"])
        self.assertIs(
            recorded["ensure_topology"][1],
            events_command.dnk_config.EVENT_BUS,
        )
        self.assertIs(
            recorded["build_publish_once_kwargs"]["broker_provider"],
            provider,
        )
        self.assertTrue(callable(recorded["build_publish_once_kwargs"]["uow_factory"]))
        self.assertIs(recorded["publish_once"], publish_once_stub)
        self.assertEqual(
            recorded["idle_sleep_seconds"],
            events_command.dnk_config.EVENT_BUS.publisher_idle_sleep_seconds,
        )
        self.assertEqual(
            recorded["error_sleep_seconds"],
            events_command.dnk_config.EVENT_BUS.publisher_error_sleep_seconds,
        )
        self.assertTrue(recorded["worker_ran"])

    async def test_handle_console_worker_runs_app_and_closes_provider(self) -> None:
        recorded = {}

        class ProviderStub:
            def __init__(self, settings) -> None:
                recorded["rabbitmq_settings"] = settings
                self.closed = False

            async def close(self) -> None:
                self.closed = True

        class AppStub:
            async def run(self) -> None:
                recorded["app_ran"] = True

        def provider_factory(settings):
            provider = ProviderStub(settings)
            recorded["provider"] = provider
            return provider

        def build_app_stub(**kwargs):
            recorded["build_app_kwargs"] = kwargs
            return AppStub()

        args = argparse.Namespace(
            queue_name="crm.contact.events",
            routing_key="crm.contact.#",
        )

        with (
            patch.object(
                events_command,
                "RabbitMQBrokerProvider",
                provider_factory,
            ),
            patch.object(
                events_command,
                "build_integration_event_console_worker_app",
                build_app_stub,
            ),
        ):
            exit_code = await events_command.handle_console_worker(args)

        provider = recorded["provider"]
        self.assertEqual(exit_code, 0)
        self.assertTrue(recorded["app_ran"])
        self.assertTrue(provider.closed)
        self.assertIs(
            recorded["rabbitmq_settings"],
            events_command.dnk_config.RABBITMQ,
        )
        self.assertIs(recorded["build_app_kwargs"]["broker_provider"], provider)
        self.assertIs(
            recorded["build_app_kwargs"]["settings"],
            events_command.dnk_config.EVENT_BUS,
        )
        self.assertEqual(
            recorded["build_app_kwargs"]["queue_name"],
            "crm.contact.events",
        )
        self.assertEqual(
            recorded["build_app_kwargs"]["routing_key"],
            "crm.contact.#",
        )


__all__ = ["EventBusManagementCommandTests"]
