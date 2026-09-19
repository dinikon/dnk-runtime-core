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

    async def schedule_once(self, job: ScheduledJob) -> bool:
        """Persists a deterministic job unless its id already exists."""
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

    async def extend_lock(
        self,
        *,
        job_id: UUID,
        lock_token: str,
        locked_until: datetime,
        updated_at: datetime,
    ) -> bool:
        """Extends a running job lease when the lock token still matches."""
        ...

    async def owns_lock(self, *, job_id: UUID, lock_token: str) -> bool:
        """Checks that a running job is still owned by the current worker."""
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

    async def cancel_matching(
        self,
        *,
        tenant_id: UUID,
        job_type: str,
        payload_contains: dict[str, object],
        canceled_at: datetime,
    ) -> int:
        """Cancels non-terminal jobs matching one tenant, type and payload."""
        ...

    async def delete_matching(
        self,
        *,
        tenant_id: UUID,
        job_type: str,
        payload_contains: dict[str, object],
    ) -> int:
        """Deletes jobs matching one tenant, type and payload."""
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
