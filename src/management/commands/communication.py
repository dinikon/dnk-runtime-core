from __future__ import annotations

import argparse
import sys

from src.modules.communication.application.use_cases import (
    ProcessQueuedMessagesCommand,
)
from src.modules.communication.domain import CommunicationError
from src.modules.communication.presentation.depends.management import (
    build_process_outbound_message_use_case,
)
from src.modules.shared.db.helper import db_helper
from src.modules.shared.db.uow import UnitOfWork


async def handle_process_queued(args: argparse.Namespace) -> int:
    """Processes queued outbound communication messages."""
    try:
        async with UnitOfWork(db_helper.session_factory) as uow:
            use_case = build_process_outbound_message_use_case(uow=uow)
            result = await use_case(
                ProcessQueuedMessagesCommand(limit=args.limit),
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
        "--limit",
        type=int,
        default=100,
        help="Maximum number of queued messages to process.",
    )
    process_queued_parser.set_defaults(handler=handle_process_queued)


__all__ = ["handle_process_queued", "register"]
