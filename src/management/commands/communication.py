from __future__ import annotations

import argparse
import sys
from uuid import UUID

from src.config import dnk_config
from src.modules.communication.application.outbound_message.command import (
    ProcessQueuedMessagesCommand,
)
from src.modules.communication.application.outbound_message.queue import (
    PublishQueuedOutboundMessagesCommand,
    RecoverStuckOutboundMessagesCommand,
)
from src.modules.communication.domain.error import CommunicationError
from src.modules.communication.infrastructure.rabbitmq import (
    RabbitMQOutboundMessagePublisher,
    build_communication_faststream_app,
)
from src.modules.communication.presentation.depends.management import (
    build_process_outbound_message_by_id_use_case,
    build_process_outbound_message_use_case,
    build_publish_queued_outbound_messages_use_case,
    build_recover_stuck_outbound_messages_use_case,
)
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.infrastructure.persistence import UnitOfWork


async def handle_process_queued(args: argparse.Namespace) -> int:
    """Processes queued outbound communication messages."""
    try:
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = build_process_outbound_message_use_case(uow=uow)
            result = await use_case(
                ProcessQueuedMessagesCommand(
                    tenant_id=UUID(args.tenant_id),
                    limit=args.limit,
                ),
            )
    except CommunicationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        "OK "
        f"processed={result.processed} "
        f"succeeded={result.succeeded} "
        f"failed={result.failed}"
    )
    return 0


async def handle_publish_queued(args: argparse.Namespace) -> int:
    """Publishes queued outbound communication messages to RabbitMQ."""
    settings = dnk_config.COMMUNICATION_QUEUE
    try:
        async with RabbitMQOutboundMessagePublisher.from_settings(
            settings,
            manage_broker_lifecycle=True,
        ) as publisher:
            async with UnitOfWork(db_helper.session_factory) as uow:
                use_case = build_publish_queued_outbound_messages_use_case(
                    uow=uow,
                    publisher=publisher,
                    republish_after_seconds=settings.republish_after_seconds,
                )
                result = await use_case(
                    PublishQueuedOutboundMessagesCommand(
                        tenant_id=UUID(args.tenant_id),
                        limit=args.limit,
                        source="republisher",
                    )
                )
    except CommunicationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(
        "OK "
        f"scanned={result.scanned} "
        f"published={result.published} "
        f"failed={result.failed}"
    )
    return 0


async def handle_recover_stuck(args: argparse.Namespace) -> int:
    """Marks expired SENDING outbound communication messages for manual recovery."""
    try:
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = build_recover_stuck_outbound_messages_use_case(uow=uow)
            result = await use_case(
                RecoverStuckOutboundMessagesCommand(
                    tenant_id=UUID(args.tenant_id),
                    older_than_seconds=args.older_than_seconds,
                    limit=args.limit,
                )
            )
    except CommunicationError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"OK recovered={result.recovered}")
    return 0


async def handle_worker(_args: argparse.Namespace) -> int:
    """Runs the FastStream RabbitMQ communication worker."""
    settings = dnk_config.COMMUNICATION_QUEUE
    processor = build_process_outbound_message_by_id_use_case(
        session_factory=db_helper.session_factory,
        processing_lease_seconds=settings.processing_lease_seconds,
    )
    app = build_communication_faststream_app(
        settings=settings,
        processor=processor,
    )
    await app.run()
    return 0


async def handle_communication_root(_args: argparse.Namespace) -> int:
    """Returns an error code for communication command group without subcommand."""
    return 1


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Registers communication management commands."""
    communication_parser = subparsers.add_parser(
        "communication",
        help="Communication management commands.",
    )
    communication_subparsers = communication_parser.add_subparsers(
        dest="communication_command"
    )
    communication_parser.set_defaults(handler=handle_communication_root)

    process_queued_parser = communication_subparsers.add_parser(
        "process-queued",
        help="Process queued outbound communication messages.",
    )
    process_queued_parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant id whose runtime communication queue should be processed.",
    )
    process_queued_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of queued messages to process.",
    )
    process_queued_parser.set_defaults(handler=handle_process_queued)

    publish_queued_parser = communication_subparsers.add_parser(
        "publish-queued",
        help="Publish queued outbound communication messages to RabbitMQ.",
    )
    publish_queued_parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant id whose queued outbound messages should be published.",
    )
    publish_queued_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of queued messages to publish.",
    )
    publish_queued_parser.set_defaults(handler=handle_publish_queued)

    recover_stuck_parser = communication_subparsers.add_parser(
        "recover-stuck",
        help="Recover expired SENDING outbound communication messages.",
    )
    recover_stuck_parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant id whose stuck outbound messages should be recovered.",
    )
    recover_stuck_parser.add_argument(
        "--older-than-seconds",
        type=int,
        default=300,
        help="Recover SENDING messages older than this many seconds.",
    )
    recover_stuck_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of stuck messages to recover.",
    )
    recover_stuck_parser.set_defaults(handler=handle_recover_stuck)

    worker_parser = communication_subparsers.add_parser(
        "worker",
        help="Run the FastStream RabbitMQ communication worker.",
    )
    worker_parser.set_defaults(handler=handle_worker)


__all__ = [
    "handle_process_queued",
    "handle_publish_queued",
    "handle_recover_stuck",
    "handle_worker",
    "register",
]
