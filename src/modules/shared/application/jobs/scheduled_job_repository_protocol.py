from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.shared.application.jobs.recover_stuck_jobs_result_dto import (
    RecoverStuckJobsResultDTO,
)
from src.modules.shared.domain.jobs import ScheduledJob


class ScheduledJobRepositoryProtocol(Protocol):
    """Persistence port for shared scheduled jobs."""

    async def schedule(self, job: ScheduledJob) -> None:
        """Persists a new scheduled job in the active UnitOfWork."""
        ...

    async def claim_due_jobs(
        self,
        *,
        limit: int,
        now: datetime,
        locked_until: datetime,
        lock_token: str,
    ) -> list[ScheduledJob]:
        """Claims due jobs for exclusive worker processing."""
        ...

    async def mark_done(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        completed_at: datetime,
    ) -> bool:
        """Marks a running job done when lock token matches."""
        ...

    async def mark_failed(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        error: str,
        retry_at: datetime | None,
        failed_at: datetime,
    ) -> bool:
        """Marks a running job failed or scheduled for retry."""
        ...

    async def cancel(self, *, job_id: UUID, canceled_at: datetime) -> bool:
        """Cancels a non-terminal job."""
        ...

    async def recover_stuck_jobs(
        self,
        *,
        limit: int,
        now: datetime,
        max_attempts: int,
    ) -> RecoverStuckJobsResultDTO:
        """Recovers expired running jobs."""
        ...


__all__ = ["ScheduledJobRepositoryProtocol"]
