from __future__ import annotations

import argparse

from src.config import dnk_config
from src.modules.shared.application.events import (
    PublishOutboxEventsCommand,
    PublishOutboxEventsUseCase,
)
from src.modules.shared.db.helper import db_helper
from src.modules.shared.db.uow import UnitOfWork
from src.modules.shared.infrastructure.events import RabbitMQIntegrationEventPublisher
from src.modules.shared.infrastructure.outbox import SqlAlchemyOutboxRepository
from src.modules.shared.infrastructure.time import UtcClock


async def handle_publish_outbox(args: argparse.Namespace) -> int:
    """Publishes due shared integration outbox events to RabbitMQ."""
    settings = dnk_config.EVENT_BUS
    async with RabbitMQIntegrationEventPublisher.from_settings(
        settings,
        manage_broker_lifecycle=True,
    ) as publisher:
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = PublishOutboxEventsUseCase(
                repository=SqlAlchemyOutboxRepository(uow.session),
                publisher=publisher,
                clock=UtcClock(),
                retry_base_seconds=settings.retry_base_seconds,
            )
            result = await use_case(
                PublishOutboxEventsCommand(
                    limit=args.limit,
                    max_attempts=args.max_attempts,
                )
            )

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
