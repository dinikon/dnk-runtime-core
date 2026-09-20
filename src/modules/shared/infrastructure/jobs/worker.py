from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.shared.application.jobs import (
    ScheduledJobDispatcherPort,
    ScheduledJobRetryPolicy,
)
from src.modules.shared.application.jobs.scheduled_job_deferred import (
    ScheduledJobDeferred,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.persistence.tenant_gate import (
    TenantGate,
)
from src.modules.shared.infrastructure.observability.metrics import (
    scheduled_job_worker_cycles,
    scheduled_job_worker_heartbeat,
    scheduled_job_worker_polls,
)

logger = logging.getLogger(__name__)


class ScheduledJobWorker:
    """Long-running short-transaction scheduled-job worker."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        dispatcher: ScheduledJobDispatcherPort,
        process_limit: int,
        recover_limit: int,
        lock_ttl_seconds: int,
        lock_heartbeat_seconds: int,
        retry_base_seconds: int,
        max_attempts: int,
        poll_interval_seconds: int,
        recover_interval_seconds: int,
        heartbeat_path: Path,
        concurrency: int = 4,
        job_timeout_seconds: float = 900,
        shutdown_grace_seconds: float = 60,
    ) -> None:
        self.session_factory = session_factory
        self.dispatcher = dispatcher
        self.process_limit = process_limit
        self.recover_limit = recover_limit
        self.lock_ttl_seconds = lock_ttl_seconds
        self.lock_heartbeat_seconds = lock_heartbeat_seconds
        self.retry_policy = ScheduledJobRetryPolicy(retry_base_seconds)
        self.max_attempts = max_attempts
        self.poll_interval_seconds = poll_interval_seconds
        self.recover_interval_seconds = recover_interval_seconds
        self.heartbeat_path = heartbeat_path
        self.concurrency = concurrency
        self.job_timeout_seconds = job_timeout_seconds
        self.shutdown_grace_seconds = shutdown_grace_seconds
        self.readiness_path = Path(str(heartbeat_path) + ".ready")
        self.tenant_gate = TenantGate(session_factory)

    async def run(self, stop: asyncio.Event) -> None:
        self.readiness_path.unlink(missing_ok=True)
        self._heartbeat()
        processing = asyncio.create_task(self._run(stop))
        try:
            while not processing.done():
                await asyncio.wait(
                    {processing}, timeout=min(self.poll_interval_seconds, 5)
                )
                if not processing.done():
                    self._heartbeat()
            await processing
        finally:
            processing.cancel()
            await asyncio.gather(processing, return_exceptions=True)
            self.readiness_path.unlink(missing_ok=True)
            self.heartbeat_path.unlink(missing_ok=True)

    async def _run(self, stop: asyncio.Event) -> None:
        last_recovery = 0.0
        active: set[asyncio.Task] = set()
        try:
            while not stop.is_set():
                for task in tuple(active):
                    if task.done():
                        active.remove(task)
                        await task
                try:
                    # Bound DB polling too: a lost TCP connection must not leave
                    # readiness true forever or prevent graceful shutdown.
                    async with asyncio.timeout(10):
                        now_monotonic = time.monotonic()
                        if (
                            now_monotonic - last_recovery
                            >= self.recover_interval_seconds
                        ):
                            await self.recover_once()
                            last_recovery = now_monotonic
                        available = self.concurrency - len(active)
                        if available:
                            jobs = await self._claim_jobs(
                                min(available, self.process_limit)
                            )
                            # No await between commit/claim and task creation: every
                            # leased job starts immediately in an available slot.
                            for job in jobs:
                                active.add(asyncio.create_task(self._process_job(job)))
                        else:
                            async with self.session_factory() as session:
                                await session.execute(text("SELECT 1"))
                        self._ready()
                except (SQLAlchemyError, OSError, TimeoutError) as exc:
                    self.readiness_path.unlink(missing_ok=True)
                    logger.warning(
                        "Scheduled-job poll unavailable: %s", type(exc).__name__
                    )
                stop_wait = asyncio.create_task(stop.wait())
                try:
                    await asyncio.wait(
                        active | {stop_wait},
                        timeout=min(self.poll_interval_seconds, 5),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                finally:
                    stop_wait.cancel()
                    await asyncio.gather(stop_wait, return_exceptions=True)
        finally:
            self.readiness_path.unlink(missing_ok=True)
            if active:
                _, pending = await asyncio.wait(
                    active, timeout=self.shutdown_grace_seconds
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*active, return_exceptions=True)

    async def _claim_jobs(self, limit: int):
        now = datetime.now(UTC)
        async with self.session_factory() as session:
            jobs = await SqlAlchemyScheduledJobRepository(session).claim_due_jobs(
                limit=limit,
                now=now,
                locked_until=now + timedelta(seconds=self.lock_ttl_seconds),
                lock_token=f"cron-{time.time_ns()}",
            )
            await session.commit()
        scheduled_job_worker_polls.labels(result="claimed" if jobs else "idle").inc()
        return jobs

    async def process_once(self) -> int:
        """One bounded concurrent batch for management/testing callers."""
        jobs = await self._claim_jobs(min(self.concurrency, self.process_limit))
        await asyncio.gather(*(self._process_job(job) for job in jobs))
        return len(jobs)

    async def _dispatch(self, job) -> None:
        async with self.tenant_gate.hold(job.tenant_id):
            await self.dispatcher.dispatch(job)

    async def _process_job(self, job) -> None:
        started = time.monotonic()
        logger.info("Scheduled job started: id=%s type=%s", job.id, job.job_type)
        lease_lost = asyncio.Event()
        heartbeat = asyncio.create_task(
            self._extend_lease(job.id, job.lock_token, lease_lost)
        )
        handler = asyncio.create_task(self._dispatch(job))
        try:
            done, _ = await asyncio.wait(
                {heartbeat, handler},
                timeout=self.job_timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                raise TimeoutError("Scheduled job exceeded its execution deadline")
            if heartbeat in done:
                await heartbeat  # Propagate DB failures and stop the handler.
                raise RuntimeError("Scheduled job lease was lost")
            await handler
            if lease_lost.is_set():
                return
            async with self.session_factory() as session:
                await SqlAlchemyScheduledJobRepository(session).mark_done(
                    job_id=job.id,
                    lock_token=job.lock_token,
                    completed_at=datetime.now(UTC),
                )
                await session.commit()
            logger.info(
                "Scheduled job completed: id=%s duration_seconds=%.3f",
                job.id,
                time.monotonic() - started,
            )
        except asyncio.CancelledError:
            # The interrupted transaction rolls back before the job is released.
            handler.cancel()
            await asyncio.gather(handler, return_exceptions=True)
            await self._release_job(job, "WorkerShutdown")
            raise
        except ScheduledJobDeferred:
            await self._release_job(job, "ResourceBusy")
        except Exception as exc:
            handler.cancel()
            await asyncio.gather(handler, return_exceptions=True)
            await self._fail_job(job, type(exc).__name__)
        finally:
            handler.cancel()
            heartbeat.cancel()
            await asyncio.gather(handler, heartbeat, return_exceptions=True)
            scheduled_job_worker_cycles.labels(phase="job").observe(
                time.monotonic() - started
            )

    async def _release_job(self, job, reason: str) -> None:
        now = datetime.now(UTC)
        try:
            async with asyncio.timeout(10):
                async with self.session_factory() as session:
                    await SqlAlchemyScheduledJobRepository(session).release_for_retry(
                        job_id=job.id,
                        lock_token=job.lock_token,
                        reason=reason,
                        retry_at=now + timedelta(seconds=30),
                        released_at=now,
                    )
                    await session.commit()
            logger.info("Scheduled job deferred: id=%s reason=%s", job.id, reason)
        except (SQLAlchemyError, OSError, TimeoutError):
            self.readiness_path.unlink(missing_ok=True)
            logger.warning("Could not release job; lease will expire: id=%s", job.id)

    async def _fail_job(self, job, error_type: str) -> None:
        logger.warning("Scheduled job failed: id=%s error_type=%s", job.id, error_type)
        failed_at = datetime.now(UTC)
        retry_at = (
            self.retry_policy.next_retry_at(now=failed_at, attempts=job.attempts)
            if job.attempts < self.max_attempts
            else None
        )
        try:
            async with asyncio.timeout(10):
                async with self.session_factory() as session:
                    await SqlAlchemyScheduledJobRepository(session).mark_failed(
                        job_id=job.id,
                        lock_token=job.lock_token,
                        error=f"{error_type}: handler failed",
                        retry_at=retry_at,
                        failed_at=failed_at,
                    )
                    await session.commit()
        except (SQLAlchemyError, OSError, TimeoutError):
            # On a DB outage the persisted lease expires; recovery requeues it.
            self.readiness_path.unlink(missing_ok=True)
            logger.warning(
                "Could not record failure; job will recover after lease expiry: id=%s",
                job.id,
            )

    def _ready(self) -> None:
        self._write_timestamp(self.readiness_path)

    async def recover_once(self) -> None:
        cycle_started = time.monotonic()
        async with self.session_factory() as session:
            await SqlAlchemyScheduledJobRepository(session).recover_stuck_jobs(
                limit=self.recover_limit,
                now=datetime.now(UTC),
                max_attempts=self.max_attempts,
            )
            await session.commit()
        scheduled_job_worker_cycles.labels(phase="recovery").observe(
            time.monotonic() - cycle_started
        )

    async def _extend_lease(self, job_id, lock_token: str, lost: asyncio.Event) -> None:
        while True:
            await asyncio.sleep(self.lock_heartbeat_seconds)
            now = datetime.now(UTC)
            async with asyncio.timeout(10):
                async with self.session_factory() as session:
                    extended = await SqlAlchemyScheduledJobRepository(
                        session
                    ).extend_lock(
                        job_id=job_id,
                        lock_token=lock_token,
                        locked_until=now + timedelta(seconds=self.lock_ttl_seconds),
                        updated_at=now,
                    )
                    await session.commit()
            if not extended:
                lost.set()
                return

    def _heartbeat(self) -> None:
        self._write_timestamp(self.heartbeat_path)
        scheduled_job_worker_heartbeat.set(datetime.now(UTC).timestamp())

    @staticmethod
    def _write_timestamp(path: Path) -> None:
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
        temporary.replace(path)
