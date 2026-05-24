from __future__ import annotations

from src.modules.shared.application.jobs.cancel_scheduled_job_command import (
    CancelScheduledJobCommand,
)
from src.modules.shared.application.jobs.cancel_scheduled_job_result_dto import (
    CancelScheduledJobResultDTO,
)
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.time import ClockPort


class CancelScheduledJobUseCase:
    """Cancels a shared scheduled job when it is not terminal."""

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
        command: CancelScheduledJobCommand,
    ) -> CancelScheduledJobResultDTO:
        canceled = await self._repository.cancel(
            job_id=command.job_id,
            canceled_at=self._clock.now(),
        )
        return CancelScheduledJobResultDTO(canceled=canceled)


__all__ = ["CancelScheduledJobUseCase"]
