from __future__ import annotations

import argparse
import asyncio
import signal

from src.config import dnk_config
from src.modules.shared.application.events import (
    OutboxPublisherWorker,
    PublishOutboxEventsCommand,
)
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence import UnitOfWork
from src.modules.shared.presentation.events import (
    build_publish_once,
    build_publish_outbox_events_use_case,
    build_rabbitmq_event_publisher_for_cli,
)
from src.modules.shared.infrastructure.events import ensure_event_bus_topology
from src.modules.shared.infrastructure.messaging import (
    RabbitMQBrokerProvider,
    RabbitMQTopologyManager,
)


async def handle_publish_outbox(args: argparse.Namespace) -> int:
    """Publishes due shared integration outbox events to RabbitMQ."""
    settings = dnk_config.EVENT_BUS
    provider, publisher = build_rabbitmq_event_publisher_for_cli(
        rabbitmq_settings=dnk_config.RABBITMQ,
        event_bus_settings=settings,
    )
    try:
        await provider.start()
        await ensure_event_bus_topology(
            RabbitMQTopologyManager(provider),
            settings,
        )
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = build_publish_outbox_events_use_case(
                session=uow.session,
                publisher=publisher,
                retry_base_seconds=settings.retry_base_seconds,
            )
            result = await use_case(
                PublishOutboxEventsCommand(
                    limit=args.limit,
                    max_attempts=args.max_attempts,
                )
            )
    finally:
        await provider.close()

    print(
        "OK "
        f"scanned={result.scanned} "
        f"published={result.published} "
        f"failed={result.failed}"
    )
    return 0


async def handle_publisher_worker(_args: argparse.Namespace) -> int:
    """Runs the long-running integration outbox publisher worker."""
    settings = dnk_config.EVENT_BUS
    provider = RabbitMQBrokerProvider(dnk_config.RABBITMQ)
    try:
        await provider.start()
        topology = RabbitMQTopologyManager(provider)
        await ensure_event_bus_topology(
            topology=topology,
            settings=settings,
        )
        publish_once = build_publish_once(
            config=dnk_config,
            uow_factory=lambda: UnitOfWork(db_helper.session_factory),
            broker_provider=provider,
        )
        worker = OutboxPublisherWorker(
            publish_once=publish_once,
            idle_sleep_seconds=settings.publisher_idle_sleep_seconds,
            error_sleep_seconds=settings.publisher_error_sleep_seconds,
        )
        _install_worker_signal_handlers(worker)
        await worker.run_forever()
    finally:
        await provider.close()
    return 0


def _install_worker_signal_handlers(worker: OutboxPublisherWorker) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except (NotImplementedError, RuntimeError):
            continue


async def handle_events_root(_args: argparse.Namespace) -> int:
    """Returns an error code for events command group without subcommand."""
    return 1


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Registers shared event bus management commands."""
    events_parser = subparsers.add_parser(
        "events",
        help="Shared integration event management commands.",
    )
    events_subparsers = events_parser.add_subparsers(dest="events_command")
    events_parser.set_defaults(handler=handle_events_root)

    publish_outbox_parser = events_subparsers.add_parser(
        "publish-outbox",
        help="Publish due integration outbox events to RabbitMQ.",
    )
    publish_outbox_parser.add_argument(
        "--limit",
        type=int,
        default=dnk_config.EVENT_BUS.publish_limit,
        help="Maximum number of due outbox events to publish.",
    )
    publish_outbox_parser.add_argument(
        "--max-attempts",
        type=int,
        default=dnk_config.EVENT_BUS.max_attempts,
        help="Maximum publish attempts before an event is failed.",
    )
    publish_outbox_parser.set_defaults(handler=handle_publish_outbox)

    publisher_worker_parser = events_subparsers.add_parser(
        "publisher-worker",
        help="Continuously publish due integration outbox events to RabbitMQ.",
    )
    publisher_worker_parser.set_defaults(handler=handle_publisher_worker)


__all__ = [
    "handle_events_root",
    "handle_publish_outbox",
    "handle_publisher_worker",
    "register",
]
