from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
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
