from __future__ import annotations

import hashlib
import asyncio
import logging
import time
from collections import Counter
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from src.modules.price_lists.application import next_cron_occurrence
from src.modules.price_lists.domain import (
    deterministic_cleanup_job_id,
    deterministic_job_id,
)
from src.modules.price_lists.infrastructure.persistence import (
    SqlAlchemyPriceListRepository,
)
from src.modules.price_lists.infrastructure.metrics import (
    price_list_sync_download_bytes,
    price_list_sync_duration,
    price_list_sync_rows,
    price_list_sync_runs,
)
from src.modules.price_lists.infrastructure.source import (
    HttpRemoteFileFetcher,
    SourceUrlCipher,
    SourceParser,
)
from src.modules.shared.domain.jobs import ScheduledJob, ScheduledJobStatus
from src.modules.shared.presentation.jobs import build_scheduled_job_repository

logger = logging.getLogger(__name__)


class PriceListSyncJobHandler:
    """Executes one price-list synchronization with short database transactions."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        fetcher: HttpRemoteFileFetcher | None = None,
        parser: SourceParser | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.fetcher = fetcher or HttpRemoteFileFetcher()
        self.parser = parser or SourceParser()

    async def handle(self, job: ScheduledJob) -> None:
        price_list_id = UUID(str(job.payload["price_list_id"]))
        revision = int(job.payload["schedule_revision"])
        trigger = str(job.payload.get("trigger") or "cron")
        price_list = await self._load_and_plan_next(
            job, price_list_id, revision, trigger
        )
        if price_list is None:
            return
        async with self._price_list_lock(job.tenant_id, price_list_id) as acquired:
            if not acquired:
                return
            await self._synchronize(job, price_list_id, revision, trigger, price_list)

    async def _synchronize(
        self,
        job: ScheduledJob,
        price_list_id: UUID,
        revision: int,
        trigger: str,
        price_list: dict,
    ) -> None:
        started = time.monotonic()
        async with self.session_factory() as session:
            repository = SqlAlchemyPriceListRepository(session)
            existing_run = await repository.get_run_by_job(
                tenant_id=job.tenant_id,
                price_list_id=price_list_id,
                scheduled_job_id=job.id,
            )
            if existing_run and existing_run["status"] in {
                "succeeded",
                "partial",
                "skipped",
            }:
                return
            if existing_run:
                run_id = existing_run["id"]
                await repository.reset_run(tenant_id=job.tenant_id, run_id=run_id)
            else:
                run_id = await repository.create_run(
                    tenant_id=job.tenant_id,
                    price_list_id=price_list_id,
                    trigger=trigger,
                    scheduled_job_id=job.id,
                    planned_at=job.run_at,
                )
            await session.commit()
        fetched = None
        try:
            fetched = await self.fetcher.fetch(
                SourceUrlCipher().decrypt(price_list["source_url_secret"])
            )
            price_list_sync_download_bytes.labels(
                format=price_list["source_format"]
            ).inc(fetched.size)
            rows = await asyncio.to_thread(
                lambda: list(
                    self.parser.rows(
                        fetched.path,
                        price_list["source_format"],
                        price_list["source_config"],
                        price_list["mapping_config"],
                    )
                )
            )
            logger.info(
                "Price-list source parsed: price_list_id=%s rows=%s bytes=%s",
                price_list_id,
                len(rows),
                fetched.size,
            )
            source_external_ids = [
                str(row.normalized["external_id"])
                for row in rows
                if row.normalized.get("external_id") not in (None, "")
            ]
            valid_external_ids = [
                str(row.normalized["external_id"]) for row in rows if not row.errors
            ]
            duplicates = [
                external_id
                for external_id, count in Counter(source_external_ids).items()
                if count > 1
            ]
            rejected = sum(bool(row.errors) for row in rows)
            if duplicates:
                raise ValueError("Source contains duplicate external_id values.")
            if not valid_external_ids or rejected / max(len(rows), 1) > 0.25:
                raise ValueError("Source validation threshold exceeded.")
            async with self.session_factory() as session:
                await self._require_current_schedule(
                    session, job, price_list_id, revision
                )
                repository = SqlAlchemyPriceListRepository(session)
                counters = await repository.apply_rows(
                    tenant_id=job.tenant_id,
                    actor_id=price_list["updated_by"],
                    price_list=price_list,
                    run_id=run_id,
                    rows=rows,
                )
                status = "partial" if counters["rejected"] else "succeeded"
                await repository.finish_run(
                    tenant_id=job.tenant_id,
                    price_list_id=price_list_id,
                    run_id=run_id,
                    status=status,
                    checksum=fetched.checksum,
                    counters=counters,
                )
                await self._require_lease(session, job)
                await session.commit()
            for result in ("read", "valid", "rejected", "created", "changed"):
                price_list_sync_rows.labels(result=result).inc(counters[result])
            price_list_sync_runs.labels(
                status=status,
                format=price_list["source_format"],
                trigger=trigger,
            ).inc()
            logger.info(
                "Partner price-list synchronization completed.",
                extra={
                    "tenant_id": str(job.tenant_id),
                    "price_list_id": str(price_list_id),
                    "sync_run_id": str(run_id),
                    "scheduled_job_id": str(job.id),
                    "sync_status": status,
                    "sync_counters": counters,
                },
            )
        except asyncio.CancelledError:
            try:
                async with asyncio.timeout(5):
                    async with self.session_factory() as session:
                        await SqlAlchemyPriceListRepository(session).finish_run(
                            tenant_id=job.tenant_id,
                            price_list_id=price_list_id,
                            run_id=run_id,
                            status="failed",
                            checksum=None,
                            counters={},
                            error="Synchronization interrupted; job may retry.",
                        )
                        await session.commit()
            except Exception:
                logger.warning(
                    "Could not record interrupted price-list run: %s", run_id
                )
            raise
        except LostJobLease:
            async with self.session_factory() as session:
                await SqlAlchemyPriceListRepository(session).skip_run(
                    tenant_id=job.tenant_id,
                    run_id=run_id,
                    reason="Synchronization was superseded by a lifecycle change.",
                )
                await session.commit()
            logger.info(
                "Partner price-list synchronization skipped after lifecycle change.",
                extra={
                    "tenant_id": str(job.tenant_id),
                    "price_list_id": str(price_list_id),
                    "sync_run_id": str(run_id),
                    "scheduled_job_id": str(job.id),
                },
            )
            return
        except Exception as exc:
            async with self.session_factory() as session:
                repository = SqlAlchemyPriceListRepository(session)
                await repository.finish_run(
                    tenant_id=job.tenant_id,
                    price_list_id=price_list_id,
                    run_id=run_id,
                    status="failed",
                    checksum=fetched.checksum if fetched else None,
                    counters={},
                    error=f"{type(exc).__name__}: synchronization failed",
                )
                await session.commit()
            price_list_sync_runs.labels(
                status="failed",
                format=price_list["source_format"],
                trigger=trigger,
            ).inc()
            logger.warning(
                "Partner price-list synchronization failed.",
                exc_info=True,
                extra={
                    "tenant_id": str(job.tenant_id),
                    "price_list_id": str(price_list_id),
                    "sync_run_id": str(run_id),
                    "scheduled_job_id": str(job.id),
                    "error_type": type(exc).__name__,
                },
            )
            raise
        finally:
            price_list_sync_duration.labels(format=price_list["source_format"]).observe(
                time.monotonic() - started
            )
            if fetched:
                Path(fetched.path).unlink(missing_ok=True)

    async def _load_and_plan_next(
        self,
        job: ScheduledJob,
        price_list_id: UUID,
        revision: int,
        trigger: str,
    ) -> dict | None:
        async with self.session_factory() as session:
            await self._require_lease(session, job)
            repository = SqlAlchemyPriceListRepository(session)
            price_list = await repository.get(job.tenant_id, price_list_id)
            if (
                price_list is None
                or price_list["status"] != "active"
                or int(price_list["schedule_revision"]) != revision
            ):
                return None
            if trigger != "manual" and price_list.get("cron_expression"):
                next_at = next_cron_occurrence(
                    price_list["cron_expression"],
                    price_list["timezone"],
                    after=max(job.run_at, datetime.now(UTC)),
                )
                next_id = deterministic_job_id(
                    job.tenant_id,
                    price_list_id,
                    revision,
                    next_at.isoformat(),
                )
                now = datetime.now(UTC)
                scheduled = ScheduledJob(
                    id=next_id,
                    tenant_id=job.tenant_id,
                    job_type="price_list.sync",
                    payload={
                        "price_list_id": str(price_list_id),
                        "schedule_revision": revision,
                        "planned_at": next_at.isoformat(),
                        "trigger": "cron",
                    },
                    run_at=next_at,
                    status=ScheduledJobStatus.SCHEDULED.value,
                    attempts=0,
                    locked_until=None,
                    lock_token=None,
                    created_at=now,
                    updated_at=now,
                )
                await build_scheduled_job_repository(session).schedule_once(scheduled)
                await repository.update_config(
                    tenant_id=job.tenant_id,
                    actor_id=price_list["updated_by"],
                    price_list_id=price_list_id,
                    values={"next_sync_at": next_at},
                )
            await session.commit()
            return price_list

    async def _require_lease(self, session: AsyncSession, job: ScheduledJob) -> None:
        if not job.lock_token:
            raise LostJobLease("Scheduled job has no lock token.")
        owns_lock = await build_scheduled_job_repository(session).owns_lock(
            job_id=job.id,
            lock_token=job.lock_token,
        )
        if not owns_lock:
            raise LostJobLease("Scheduled job lease was lost.")

    async def _require_current_schedule(
        self,
        session: AsyncSession,
        job: ScheduledJob,
        price_list_id: UUID,
        revision: int,
    ) -> None:
        await self._require_lease(session, job)
        current = await SqlAlchemyPriceListRepository(session).get(
            job.tenant_id, price_list_id
        )
        if (
            current is None
            or current["status"] != "active"
            or int(current["schedule_revision"]) != revision
        ):
            raise LostJobLease("Price-list schedule is no longer current.")

    @asynccontextmanager
    async def _price_list_lock(
        self, tenant_id: UUID, price_list_id: UUID
    ) -> AsyncIterator[bool]:
        """Serializes syncs for one tenant/price-list on PostgreSQL."""
        digest = hashlib.sha256(f"{tenant_id}:{price_list_id}".encode()).digest()
        lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
        bind = self.session_factory.kw["bind"]
        engine = bind.engine if isinstance(bind, AsyncConnection) else bind
        # Pin the physical connection until unlock: committing an AsyncSession
        # alone would return a still-locked connection to the pool.
        async with engine.connect() as connection:
            if connection.dialect.name != "postgresql":
                yield True
                return
            acquired = bool(
                await connection.scalar(
                    text("SELECT pg_try_advisory_lock(:lock_key)"),
                    {"lock_key": lock_key},
                )
            )
            try:
                await connection.commit()
                yield acquired
            finally:
                if acquired:
                    try:
                        await connection.rollback()
                        await asyncio.shield(
                            connection.execute(
                                text("SELECT pg_advisory_unlock(:lock_key)"),
                                {"lock_key": lock_key},
                            )
                        )
                        await connection.commit()
                    except BaseException:
                        await connection.invalidate()
                        raise


class LostJobLease(RuntimeError):
    """Raised when a recovered job must no longer mutate business state."""


class PriceListCleanupJobHandler:
    """Deletes diagnostic staging rows from failed runs after seven days."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def handle(self, job: ScheduledJob) -> None:
        if not job.lock_token:
            raise LostJobLease("Scheduled job has no lock token.")
        now = datetime.now(UTC)
        next_at = (now + timedelta(days=1)).replace(
            hour=3, minute=0, second=0, microsecond=0
        )
        async with self.session_factory() as session:
            scheduled_jobs = build_scheduled_job_repository(session)
            if not await scheduled_jobs.owns_lock(
                job_id=job.id, lock_token=job.lock_token
            ):
                raise LostJobLease("Scheduled job lease was lost.")
            deleted = await SqlAlchemyPriceListRepository(
                session
            ).cleanup_failed_staging(
                tenant_id=job.tenant_id,
                older_than=now - timedelta(days=7),
            )
            next_job = ScheduledJob(
                id=deterministic_cleanup_job_id(job.tenant_id, next_at.isoformat()),
                tenant_id=job.tenant_id,
                job_type="price_list.cleanup",
                payload={"planned_at": next_at.isoformat()},
                run_at=next_at,
                status=ScheduledJobStatus.SCHEDULED.value,
                attempts=0,
                locked_until=None,
                lock_token=None,
                created_at=now,
                updated_at=now,
            )
            await scheduled_jobs.schedule_once(next_job)
            if not await scheduled_jobs.owns_lock(
                job_id=job.id, lock_token=job.lock_token
            ):
                raise LostJobLease("Scheduled job lease was lost.")
            await session.commit()
        logger.info(
            "Partner price-list staging cleanup completed.",
            extra={
                "tenant_id": str(job.tenant_id),
                "scheduled_job_id": str(job.id),
                "deleted_rows": deleted,
            },
        )
