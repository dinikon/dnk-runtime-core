from __future__ import annotations

from src.modules.shared.application.jobs.recover_stuck_jobs_result_dto import (
    RecoverStuckJobsResultDTO,
)
from src.modules.shared.application.jobs.recover_stuck_scheduled_jobs_command import (
    RecoverStuckScheduledJobsCommand,
)
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.time import ClockPort


class RecoverStuckScheduledJobsUseCase:
    """Recovers running jobs whose worker lock has expired."""

    def __init__(
        self,
        *,
        repository: ScheduledJobRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        self._repository = repository
        self._clock = clock

    async def __call__(
        self,
        command: RecoverStuckScheduledJobsCommand,
    ) -> RecoverStuckJobsResultDTO:
        return await self._repository.recover_stuck_jobs(
            limit=command.limit,
            now=self._clock.now(),
            max_attempts=command.max_attempts,
        )


__all__ = ["RecoverStuckScheduledJobsUseCase"]
