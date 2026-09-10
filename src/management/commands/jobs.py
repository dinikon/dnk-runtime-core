from __future__ import annotations

import argparse

from src.config import dnk_config
from src.modules.shared.application.jobs import (
    ProcessDueScheduledJobsCommand,
    RecoverStuckScheduledJobsCommand,
)
from src.modules.shared.infrastructure.persistence import UnitOfWork
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.shared.presentation.jobs import (
    build_process_due_scheduled_jobs_use_case,
    build_recover_stuck_scheduled_jobs_use_case,
)


async def handle_process_due(args: argparse.Namespace) -> int:
    """Processes due shared scheduled jobs."""
    settings = dnk_config.SCHEDULED_JOBS
    async with UnitOfWork(db_helper.session_factory) as uow:
        use_case = build_process_due_scheduled_jobs_use_case(
            session=uow.session,
            retry_base_seconds=settings.retry_base_seconds,
        )
        result = await use_case(
            ProcessDueScheduledJobsCommand(
                limit=args.limit,
                max_attempts=args.max_attempts,
                lock_ttl_seconds=args.lock_ttl_seconds,
            )
        )

    print(
        "OK "
        f"scanned={result.scanned} "
        f"processed={result.processed} "
        f"done={result.done} "
        f"failed={result.failed} "
        f"retried={result.retried}"
    )
    return 0


async def handle_recover_stuck(args: argparse.Namespace) -> int:
    """Recovers expired running shared scheduled jobs."""
    async with UnitOfWork(db_helper.session_factory) as uow:
        use_case = build_recover_stuck_scheduled_jobs_use_case(session=uow.session)
        result = await use_case(
            RecoverStuckScheduledJobsCommand(
                limit=args.limit,
                max_attempts=args.max_attempts,
            )
        )

    print(
        "OK "
        f"scanned={result.scanned} "
        f"recovered={result.recovered} "
        f"failed={result.failed}"
    )
    return 0


async def handle_jobs_root(_args: argparse.Namespace) -> int:
    """Returns an error code for jobs command group without subcommand."""
    return 1


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Registers shared scheduled jobs management commands."""
    settings = dnk_config.SCHEDULED_JOBS
    jobs_parser = subparsers.add_parser(
        "jobs",
        help="Shared scheduled jobs management commands.",
    )
    jobs_subparsers = jobs_parser.add_subparsers(dest="jobs_command")
    jobs_parser.set_defaults(handler=handle_jobs_root)

    process_due_parser = jobs_subparsers.add_parser(
        "process-due",
        help="Process due shared scheduled jobs.",
    )
    process_due_parser.add_argument(
        "--limit",
        type=int,
        default=settings.process_limit,
        help="Maximum number of due scheduled jobs to process.",
    )
    process_due_parser.add_argument(
        "--max-attempts",
        type=int,
        default=settings.max_attempts,
        help="Maximum attempts before a scheduled job is failed.",
    )
    process_due_parser.add_argument(
        "--lock-ttl-seconds",
        type=int,
        default=settings.lock_ttl_seconds,
        help="Worker lock TTL in seconds for claimed jobs.",
    )
    process_due_parser.set_defaults(handler=handle_process_due)

    recover_stuck_parser = jobs_subparsers.add_parser(
        "recover-stuck",
        help="Recover expired running shared scheduled jobs.",
    )
    recover_stuck_parser.add_argument(
        "--limit",
        type=int,
        default=settings.recover_limit,
        help="Maximum number of stuck scheduled jobs to recover.",
    )
    recover_stuck_parser.add_argument(
        "--max-attempts",
        type=int,
        default=settings.max_attempts,
        help="Maximum attempts before a stuck scheduled job is failed.",
    )
    recover_stuck_parser.set_defaults(handler=handle_recover_stuck)


__all__ = [
    "handle_jobs_root",
    "handle_process_due",
    "handle_recover_stuck",
    "register",
]
