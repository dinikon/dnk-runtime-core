from __future__ import annotations

from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_result_dto import (
    ScheduleScheduledJobResultDTO,
)
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.application.uuid import UUIdGeneratorProtocol
from src.modules.shared.domain.jobs import ScheduledJob, ScheduledJobStatus
from src.modules.shared.domain.time import ClockPort


class ScheduleScheduledJobUseCase:
    """Schedules a shared deferred job in the caller's active UnitOfWork."""

    def __init__(
        self,
        *,
        repository: ScheduledJobRepositoryProtocol,
        clock: ClockPort,
        uuid_generator: UUIdGeneratorProtocol,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._uuid_generator = uuid_generator

    async def __call__(
        self,
        command: ScheduleScheduledJobCommand,
    ) -> ScheduleScheduledJobResultDTO:
        now = self._clock.now()
        job = ScheduledJob(
            id=command.job_id or self._uuid_generator.new(),
            tenant_id=command.tenant_id,
            job_type=command.job_type,
            payload=dict(command.payload),
            run_at=command.run_at,
            status=ScheduledJobStatus.SCHEDULED.value,
            attempts=0,
            locked_until=None,
            lock_token=None,
            created_at=now,
            updated_at=now,
            last_error=None,
        )
        await self._repository.schedule(job)
        return ScheduleScheduledJobResultDTO(job=job)


__all__ = ["ScheduleScheduledJobUseCase"]
