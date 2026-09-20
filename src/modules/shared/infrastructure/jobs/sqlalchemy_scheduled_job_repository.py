from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.application.jobs import RecoverStuckJobsResultDTO
from src.modules.shared.domain.jobs import ScheduledJob, ScheduledJobStatus
from src.modules.shared.infrastructure.jobs.scheduled_job_model import (
    ScheduledJobModel,
)


class SqlAlchemyScheduledJobRepository:
    """SQLAlchemy-backed scheduled job repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def schedule(self, job: ScheduledJob) -> None:
        """Adds a new scheduled job to the current UnitOfWork."""
        self._session.add(
            ScheduledJobModel(
                id=job.id,
                tenant_id=job.tenant_id,
                job_type=job.job_type,
                payload=dict(job.payload),
                run_at=job.run_at,
                status=ScheduledJobStatus.SCHEDULED.value,
                attempts=0,
                locked_until=None,
                lock_token=None,
                created_at=job.created_at,
                updated_at=job.updated_at,
                last_error=None,
            )
        )
        await self._session.flush()

    async def schedule_once(self, job: ScheduledJob) -> bool:
        """Inserts a caller-identified job idempotently."""
        values = {
            "id": job.id,
            "tenant_id": job.tenant_id,
            "job_type": job.job_type,
            "payload": dict(job.payload),
            "run_at": job.run_at,
            "status": ScheduledJobStatus.SCHEDULED.value,
            "attempts": 0,
            "locked_until": None,
            "lock_token": None,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "last_error": None,
        }
        dialect = (
            self._session.bind.dialect.name if self._session.bind else "postgresql"
        )
        statement = insert(ScheduledJobModel).values(**values)
        if dialect == "postgresql":
            statement = (
                postgresql_insert(ScheduledJobModel)
                .values(**values)
                .on_conflict_do_nothing(index_elements=[ScheduledJobModel.id])
            )
        result = await self._session.execute(statement)
        await self._session.flush()
        return bool(result.rowcount)

    async def claim_due_jobs(
        self,
        *,
        limit: int,
        now: datetime,
        locked_until: datetime,
        lock_token: str,
    ) -> list[ScheduledJob]:
        """Claims due scheduled jobs using row-level locks."""
        if limit <= 0:
            return []

        models = list(
            (
                await self._session.scalars(
                    select(ScheduledJobModel)
                    .where(
                        ScheduledJobModel.status == ScheduledJobStatus.SCHEDULED.value
                    )
                    .where(ScheduledJobModel.run_at <= now)
                    .order_by(ScheduledJobModel.run_at, ScheduledJobModel.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for model in models:
            model.status = ScheduledJobStatus.RUNNING.value
            model.attempts = int(model.attempts or 0) + 1
            model.locked_until = locked_until
            model.lock_token = lock_token
            model.last_error = None
            model.updated_at = now
        await self._session.flush()
        return [_scheduled_job(model) for model in models]

    async def mark_done(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        completed_at: datetime,
    ) -> bool:
        """Marks a running job done when the lock token matches."""
        result = await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id)
            .where(ScheduledJobModel.status == ScheduledJobStatus.RUNNING.value)
            .where(ScheduledJobModel.lock_token == lock_token)
            .values(
                status=ScheduledJobStatus.DONE.value,
                locked_until=None,
                lock_token=None,
                last_error=None,
                updated_at=completed_at,
            )
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def extend_lock(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        locked_until: datetime,
        updated_at: datetime,
    ) -> bool:
        result = await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id)
            .where(ScheduledJobModel.status == ScheduledJobStatus.RUNNING.value)
            .where(ScheduledJobModel.lock_token == lock_token)
            .values(locked_until=locked_until, updated_at=updated_at)
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def owns_lock(self, *, job_id: UUID, lock_token: str) -> bool:
        result = await self._session.execute(
            select(ScheduledJobModel.id)
            .where(ScheduledJobModel.id == job_id)
            .where(ScheduledJobModel.status == ScheduledJobStatus.RUNNING.value)
            .where(ScheduledJobModel.lock_token == lock_token)
        )
        return result.scalar_one_or_none() is not None

    async def terminal_or_missing(
        self, *, tenant_id: UUID, job_ids: list[UUID]
    ) -> set[UUID]:
        """Finds jobs that cannot be recovered or retried by a worker."""
        if not job_ids:
            return set()
        result = await self._session.execute(
            select(ScheduledJobModel.id).where(
                ScheduledJobModel.tenant_id == tenant_id,
                ScheduledJobModel.id.in_(job_ids),
                ScheduledJobModel.status.in_(("scheduled", "running")),
            )
        )
        return set(job_ids) - set(result.scalars())

    async def owns_current_lease(
        self,
        *,
        job_id: UUID,
        tenant_id: UUID,
        lock_token: str,
        for_update: bool = False,
    ) -> bool:
        """Fences business publication against cancellation and lease recovery."""
        from datetime import UTC

        now = (
            func.clock_timestamp()
            if self._session.bind.dialect.name == "postgresql"
            else datetime.now(UTC)
        )
        statement = select(ScheduledJobModel.id).where(
            ScheduledJobModel.id == job_id,
            ScheduledJobModel.tenant_id == tenant_id,
            ScheduledJobModel.status == ScheduledJobStatus.RUNNING.value,
            ScheduledJobModel.lock_token == lock_token,
            ScheduledJobModel.locked_until > now,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def mark_failed(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        error: str,
        retry_at: datetime | None,
        failed_at: datetime,
    ) -> bool:
        """Marks a running job failed or returns it to scheduled retry."""
        status = (
            ScheduledJobStatus.FAILED.value
            if retry_at is None
            else ScheduledJobStatus.SCHEDULED.value
        )
        values = {
            "status": status,
            "locked_until": None,
            "lock_token": None,
            "last_error": error,
            "updated_at": failed_at,
        }
        if retry_at is not None:
            values["run_at"] = retry_at

        result = await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id)
            .where(ScheduledJobModel.status == ScheduledJobStatus.RUNNING.value)
            .where(ScheduledJobModel.lock_token == lock_token)
            .values(**values)
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def release_for_retry(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        reason: str,
        retry_at: datetime,
        released_at: datetime,
    ) -> bool:
        """Release contention/shutdown without exhausting the failure budget."""
        result = await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id)
            .where(ScheduledJobModel.status == ScheduledJobStatus.RUNNING.value)
            .where(ScheduledJobModel.lock_token == lock_token)
            .values(
                status=ScheduledJobStatus.SCHEDULED.value,
                attempts=func.greatest(ScheduledJobModel.attempts - 1, 0),
                run_at=retry_at,
                locked_until=None,
                lock_token=None,
                last_error=reason,
                updated_at=released_at,
            )
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def cancel(self, *, job_id: UUID, canceled_at: datetime) -> bool:
        """Cancels a non-terminal job."""
        result = await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.id == job_id)
            .where(
                ScheduledJobModel.status.not_in(
                    [
                        ScheduledJobStatus.DONE.value,
                        ScheduledJobStatus.FAILED.value,
                        ScheduledJobStatus.CANCELED.value,
                    ]
                )
            )
            .values(
                status=ScheduledJobStatus.CANCELED.value,
                locked_until=None,
                lock_token=None,
                updated_at=canceled_at,
            )
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def cancel_matching(
        self,
        *,
        tenant_id: UUID,
        job_type: str,
        payload_contains: dict[str, object],
        canceled_at: datetime,
    ) -> int:
        """Cancels all matching scheduled or running jobs and revokes leases."""
        result = await self._session.execute(
            update(ScheduledJobModel)
            .where(ScheduledJobModel.tenant_id == tenant_id)
            .where(ScheduledJobModel.job_type == job_type)
            .where(ScheduledJobModel.payload.contains(payload_contains))
            .where(
                ScheduledJobModel.status.in_(
                    [
                        ScheduledJobStatus.SCHEDULED.value,
                        ScheduledJobStatus.RUNNING.value,
                    ]
                )
            )
            .values(
                status=ScheduledJobStatus.CANCELED.value,
                locked_until=None,
                lock_token=None,
                updated_at=canceled_at,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def delete_matching(
        self,
        *,
        tenant_id: UUID,
        job_type: str,
        payload_contains: dict[str, object],
    ) -> int:
        """Deletes all matching jobs after their owning entity is archived."""
        result = await self._session.execute(
            delete(ScheduledJobModel)
            .where(ScheduledJobModel.tenant_id == tenant_id)
            .where(ScheduledJobModel.job_type == job_type)
            .where(ScheduledJobModel.payload.contains(payload_contains))
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def recover_stuck_jobs(
        self,
        *,
        limit: int,
        now: datetime,
        max_attempts: int,
    ) -> RecoverStuckJobsResultDTO:
        """Returns expired running jobs to schedule or fails exhausted ones."""
        if limit <= 0:
            return RecoverStuckJobsResultDTO(scanned=0, recovered=0, failed=0)

        models = list(
            (
                await self._session.scalars(
                    select(ScheduledJobModel)
                    .where(ScheduledJobModel.status == ScheduledJobStatus.RUNNING.value)
                    .where(ScheduledJobModel.locked_until <= now)
                    .order_by(ScheduledJobModel.locked_until, ScheduledJobModel.id)
                    .limit(limit)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        recovered = 0
        failed = 0
        for model in models:
            if int(model.attempts or 0) >= max_attempts:
                model.status = ScheduledJobStatus.FAILED.value
                failed += 1
            else:
                model.status = ScheduledJobStatus.SCHEDULED.value
                model.run_at = now
                recovered += 1
            model.locked_until = None
            model.lock_token = None
            model.last_error = "Job lock expired."
            model.updated_at = now
        await self._session.flush()
        return RecoverStuckJobsResultDTO(
            scanned=len(models),
            recovered=recovered,
            failed=failed,
        )


def _scheduled_job(model: ScheduledJobModel) -> ScheduledJob:
    return ScheduledJob(
        id=model.id,
        tenant_id=model.tenant_id,
        job_type=model.job_type,
        payload=dict(model.payload or {}),
        run_at=model.run_at,
        status=model.status,
        attempts=int(model.attempts or 0),
        locked_until=model.locked_until,
        lock_token=model.lock_token,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_error=model.last_error,
    )


__all__ = ["SqlAlchemyScheduledJobRepository"]
