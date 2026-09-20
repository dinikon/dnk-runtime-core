from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
import signal

from sqlalchemy import text

from src.config import dnk_config
from src.modules.shared.application.jobs import (
    ProcessDueScheduledJobsCommand,
    RecoverStuckScheduledJobsCommand,
)
from src.modules.shared.infrastructure.persistence import UnitOfWork
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
from src.modules.price_lists.presentation.jobs import (
    PriceListCleanupJobHandler,
    PriceListSyncJobHandler,
)
from src.modules.shared.presentation.jobs import (
    build_process_due_scheduled_jobs_use_case,
    build_recover_stuck_scheduled_jobs_use_case,
    build_scheduled_job_dispatcher,
    build_scheduled_job_worker,
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


async def handle_worker(_args: argparse.Namespace) -> int:
    """Runs the production scheduled-jobs polling worker until a signal arrives."""
    logging.basicConfig(level=logging.INFO)
    await db_helper.initialize_for_startup()
    settings = dnk_config.SCHEDULED_JOBS
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for event in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(event, stop.set)
        except NotImplementedError:
            pass
    dispatcher = build_scheduled_job_dispatcher(
        {
            "price_list.sync": PriceListSyncJobHandler(db_helper.session_factory),
            "price_list.cleanup": PriceListCleanupJobHandler(db_helper.session_factory),
        }
    )
    worker = build_scheduled_job_worker(
        session_factory=db_helper.session_factory,
        dispatcher=dispatcher,
        process_limit=settings.process_limit,
        recover_limit=settings.recover_limit,
        lock_ttl_seconds=settings.lock_ttl_seconds,
        lock_heartbeat_seconds=settings.lock_heartbeat_seconds,
        retry_base_seconds=settings.retry_base_seconds,
        max_attempts=settings.max_attempts,
        poll_interval_seconds=settings.poll_interval_seconds,
        recover_interval_seconds=settings.recover_interval_seconds,
        heartbeat_path=Path(settings.heartbeat_path),
    )
    try:
        await worker.run(stop)
        return 0
    finally:
        await db_helper.dispose()


async def handle_healthcheck(_args: argparse.Namespace) -> int:
    """Checks the worker heartbeat and the PostgreSQL connection."""
    settings = dnk_config.SCHEDULED_JOBS
    heartbeat = Path(settings.heartbeat_path)
    if not heartbeat.exists():
        return 1
    try:
        last = datetime.fromisoformat(heartbeat.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 1
    max_age = max(settings.poll_interval_seconds * 5, 30)
    if (datetime.now(UTC) - last).total_seconds() > max_age:
        return 1
    try:
        async with db_helper.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return 1
    return 0


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

    worker_parser = jobs_subparsers.add_parser(
        "worker",
        help="Run the long-lived shared scheduled jobs worker.",
    )
    worker_parser.set_defaults(handler=handle_worker)

    healthcheck_parser = jobs_subparsers.add_parser(
        "healthcheck",
        help="Check CronWorker heartbeat and database connectivity.",
    )
    healthcheck_parser.set_defaults(handler=handle_healthcheck)


__all__ = [
    "handle_jobs_root",
    "handle_process_due",
    "handle_recover_stuck",
    "handle_worker",
    "handle_healthcheck",
    "register",
]
