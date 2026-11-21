from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
import signal
from datetime import UTC, datetime

from src.modules.files.presentation.jobs.empty_trash import (
    FilesEmptyTrashJobHandler,
    JOB_TYPE as FILES_EMPTY_TRASH_JOB_TYPE,
)
from src.modules.files.presentation.jobs.purge_file import (
    FilesPurgeJobHandler,
    JOB_TYPE as FILES_PURGE_JOB_TYPE,
)
from src.modules.files.presentation.jobs.trash_cleanup import (
    FilesTrashCleanupJobHandler,
    ensure_trash_cleanup_jobs,
    JOB_TYPE as FILES_TRASH_JOB_TYPE,
)
from src.config import dnk_config
from src.modules.channels.presentation.jobs.verify_connection import (
    ChannelsVerifyConnectionJobHandler,
)
from src.modules.channels.infrastructure.jobs import (
    JOB_TYPE as CHANNELS_VERIFY_JOB_TYPE,
)
from src.modules.reference_data.presentation.jobs.refresh import (
    JOB_TYPE,
    ReferenceDataRefreshJobHandler,
    ensure_weekly_jobs,
)
from src.management.job_healthcheck import main as probe_main
from src.modules.shared.application.jobs import (
    ProcessDueScheduledJobsCommand,
    RecoverStuckScheduledJobsCommand,
)
from src.modules.shared.infrastructure.persistence import UnitOfWork
from src.modules.shared.infrastructure.persistence.database_helper import db_helper
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
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("src.modules").setLevel(logging.INFO)
    await db_helper.initialize_for_startup()
    settings = dnk_config.SCHEDULED_JOBS
    stop = asyncio.Event()
    if dnk_config.SQLALCHEMY_POOL_SIZE and (
        dnk_config.SQLALCHEMY_POOL_SIZE + dnk_config.SQLALCHEMY_MAX_OVERFLOW
        < 4 * settings.concurrency + 2
    ):
        raise ValueError(
            "Cron DB pool requires at least 4 * concurrency + 2 connections"
        )
    loop = asyncio.get_running_loop()
    for event in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(event, stop.set)
        except NotImplementedError:
            pass
    from src.modules.files.presentation.jobs.cleanup import (
        FilesCleanupJobHandler,
        ensure_cleanup_jobs,
        JOB_TYPE as FILES_CLEANUP_JOB_TYPE,
    )

    from src.modules.catalog.presentation.catalog_import.jobs import (
        CatalogImportJobHandler,
    )
    from src.modules.catalog.presentation.catalog_import.maintenance_job import (
        CatalogImportMaintenanceJobHandler,
    )

    catalog_imports = CatalogImportJobHandler(db_helper.session_factory)
    dispatcher = build_scheduled_job_dispatcher(
        {
            CHANNELS_VERIFY_JOB_TYPE: ChannelsVerifyConnectionJobHandler(
                db_helper.session_factory
            ),
            JOB_TYPE: ReferenceDataRefreshJobHandler(db_helper.session_factory),
            "catalog.import.prepare": catalog_imports,
            "catalog.import.run": catalog_imports,
            "catalog.import.maintain": CatalogImportMaintenanceJobHandler(
                db_helper.session_factory
            ),
            FILES_CLEANUP_JOB_TYPE: FilesCleanupJobHandler(db_helper.session_factory),
            FILES_PURGE_JOB_TYPE: FilesPurgeJobHandler(db_helper.session_factory),
            FILES_EMPTY_TRASH_JOB_TYPE: FilesEmptyTrashJobHandler(
                db_helper.session_factory
            ),
            FILES_TRASH_JOB_TYPE: FilesTrashCleanupJobHandler(
                db_helper.session_factory
            ),
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
        concurrency=settings.concurrency,
        job_timeout_seconds=settings.job_timeout_seconds,
        shutdown_grace_seconds=settings.shutdown_grace_seconds,
    )

    async def register_recurring_jobs() -> None:
        """Регистрирует периодические задания независимо при сбое одного из модулей."""
        logger = logging.getLogger(__name__)
        registrars = (
            ("reference_data", ensure_weekly_jobs),
            ("files.orphans", ensure_cleanup_jobs),
            ("files.trash", ensure_trash_cleanup_jobs),
        )
        while not stop.is_set():
            for kind, register_jobs in registrars:
                try:
                    await register_jobs(db_helper.session_factory, datetime.now(UTC))
                except Exception as error:
                    logger.warning(
                        "Recurring job registration failed",
                        extra={
                            "event": "jobs.registration.failed",
                            "job_kind": kind,
                            "error_type": type(error).__name__,
                        },
                    )
            try:
                await asyncio.wait_for(stop.wait(), timeout=3600)
            except TimeoutError:
                pass

    registrar = asyncio.create_task(register_recurring_jobs())
    try:
        await worker.run(stop)
        return 0
    finally:
        registrar.cancel()
        await asyncio.gather(registrar, return_exceptions=True)
        await db_helper.dispose()


async def handle_healthcheck(args: argparse.Namespace) -> int:
    """Use the same lightweight probe for programmatic parser callers."""
    return probe_main(["--liveness"] if getattr(args, "liveness", False) else [])


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
        help="Check worker heartbeat and its last successful database poll.",
    )
    healthcheck_parser.add_argument("--liveness", action="store_true")
    healthcheck_parser.set_defaults(handler=handle_healthcheck)


__all__ = [
    "handle_jobs_root",
    "handle_process_due",
    "handle_recover_stuck",
    "handle_worker",
    "handle_healthcheck",
    "register",
]
