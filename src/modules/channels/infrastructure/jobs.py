from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from datetime import datetime
from uuid import UUID
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)

VERIFY_JOB = "channels.verify_connection"
PAGE_JOB = "channels.initialize_publications"


class ScheduledChannelsJobs:
    """Адаптирует конкретные Channels intents к общей durable очереди."""

    def __init__(
        self,
        scheduler: ScheduleScheduledJobUseCase,
        repository: ScheduledJobRepositoryProtocol,
    ) -> None:
        """Принимает scheduler общей сессии, уже защищённой tenant admission."""
        self.scheduler = scheduler
        self.repository = repository

    async def verification(
        self,
        tenant_id: UUID,
        channel_id: UUID,
        job_id: UUID,
        generation: int,
        actor_id: UUID,
        now: datetime,
    ) -> None:
        """Планирует проверку с одними ID и generation в payload."""
        await self.scheduler(
            ScheduleScheduledJobCommand(
                tenant_id,
                VERIFY_JOB,
                {
                    "channel_id": str(channel_id),
                    "generation": generation,
                    "actor_id": str(actor_id),
                },
                now,
                job_id,
            )
        )

    async def page(
        self, tenant_id: UUID, run_id: UUID, job_id: UUID, sequence: int, now: datetime
    ) -> None:
        """Планирует страницу с устойчивым job ID и номером шага."""
        await self.scheduler(
            ScheduleScheduledJobCommand(
                tenant_id,
                PAGE_JOB,
                {"run_id": str(run_id), "sequence": sequence},
                now,
                job_id,
            )
        )

    async def is_recoverable(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Читает статус через public shared contract, без foreign ORM."""
        terminal = await self.repository.terminal_or_missing(
            tenant_id=tenant_id, job_ids=[job_id]
        )
        return job_id not in terminal
