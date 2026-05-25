from __future__ import annotations

import argparse

from src.config import dnk_config
from src.modules.shared.application.events import PublishOutboxEventsCommand
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence import UnitOfWork
from src.modules.shared.presentation.events import (
    build_publish_outbox_events_use_case,
    build_rabbitmq_event_publisher_for_cli,
)
from src.modules.shared.infrastructure.events import ensure_event_bus_topology
from src.modules.shared.infrastructure.messaging import RabbitMQTopologyManager


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


__all__ = [
    "handle_events_root",
    "handle_publish_outbox",
    "register",
]
