from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.shared.application.jobs import (
    ScheduledJobDispatcherPort,
    ScheduledJobRetryPolicy,
)
from src.modules.shared.infrastructure.jobs.sqlalchemy_scheduled_job_repository import (
    SqlAlchemyScheduledJobRepository,
)
from src.modules.shared.infrastructure.persistence.tenant_gate import (
    TenantGate,
    TenantUnavailable,
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
        self.tenant_gate = TenantGate(session_factory)

    async def run(self, stop: asyncio.Event) -> None:
        # A healthy import can take longer than the probe's maximum heartbeat
        # age. Keep reporting event-loop liveness while the poll is in progress.
        self._heartbeat()
        processing = asyncio.create_task(self._run(stop))
        try:
            while not processing.done():
                await asyncio.wait({processing}, timeout=self.poll_interval_seconds)
                if not processing.done():
                    self._heartbeat()
            await processing
        finally:
            processing.cancel()
            await asyncio.gather(processing, return_exceptions=True)

    async def _run(self, stop: asyncio.Event) -> None:
        last_recovery = 0.0
        while not stop.is_set():
            now_monotonic = time.monotonic()
            if now_monotonic - last_recovery >= self.recover_interval_seconds:
                await self.recover_once()
                last_recovery = now_monotonic
            processed = await self.process_once()
            self._heartbeat()
            if not processed:
                try:
                    await asyncio.wait_for(
                        stop.wait(), timeout=self.poll_interval_seconds
                    )
                except TimeoutError:
                    pass

    async def process_once(self) -> int:
        cycle_started = time.monotonic()
        now = datetime.now(UTC)
        lock_token = f"cron-{time.time_ns()}"
        async with self.session_factory() as session:
            repository = SqlAlchemyScheduledJobRepository(session)
            jobs = await repository.claim_due_jobs(
                # Execution is serial: queued jobs must not consume their lease
                # or attempts while a preceding import is still running.
                limit=min(self.process_limit, 1),
                now=now,
                locked_until=now + timedelta(seconds=self.lock_ttl_seconds),
                lock_token=lock_token,
            )
            await session.commit()
        scheduled_job_worker_polls.labels(result="claimed" if jobs else "idle").inc()
        for job in jobs:
            logger.info("Scheduled job started: id=%s type=%s", job.id, job.job_type)
            lease_lost = asyncio.Event()
            heartbeat = asyncio.create_task(
                self._extend_lease(job.id, lock_token, lease_lost)
            )
            try:
                async with self.tenant_gate.hold(job.tenant_id):
                    await self.dispatcher.dispatch(job)
                if lease_lost.is_set():
                    continue
                async with self.session_factory() as session:
                    await SqlAlchemyScheduledJobRepository(session).mark_done(
                        job_id=job.id,
                        lock_token=lock_token,
                        completed_at=datetime.now(UTC),
                    )
                    await session.commit()
                logger.info("Scheduled job completed: id=%s", job.id)
            except TenantUnavailable:
                continue
            except Exception as exc:
                logger.warning(
                    "Scheduled job failed: id=%s error_type=%s",
                    job.id,
                    type(exc).__name__,
                )
                failed_at = datetime.now(UTC)
                retry_at = None
                if job.attempts < self.max_attempts:
                    retry_at = self.retry_policy.next_retry_at(
                        now=failed_at, attempts=job.attempts
                    )
                async with self.session_factory() as session:
                    await SqlAlchemyScheduledJobRepository(session).mark_failed(
                        job_id=job.id,
                        lock_token=lock_token,
                        error=f"{type(exc).__name__}: handler failed",
                        retry_at=retry_at,
                        failed_at=failed_at,
                    )
                    await session.commit()
            finally:
                heartbeat.cancel()
                await asyncio.gather(heartbeat, return_exceptions=True)
        scheduled_job_worker_cycles.labels(phase="poll").observe(
            time.monotonic() - cycle_started
        )
        return len(jobs)

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
            async with self.session_factory() as session:
                extended = await SqlAlchemyScheduledJobRepository(session).extend_lock(
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
        now = datetime.now(UTC)
        self.heartbeat_path.write_text(now.isoformat(), encoding="utf-8")
        scheduled_job_worker_heartbeat.set(now.timestamp())
