from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from datetime import datetime
from uuid import UUID, uuid5
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)

VERIFY_JOB = "channels.verify_connection"
PAGE_JOB = "channels.initialize_publications"
IMPORT_JOB = "channels.prepare_publication_import"
IMPORT_CLEANUP_JOB = "channels.cleanup_publication_import"
CONTENT_UPDATE_JOB = "channels.update_publication_content"


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

    async def prepare(
        self, tenant_id: UUID, preparation_id: UUID, sequence: int, now: datetime
    ) -> None:
        """Планирует одну карточку или фотографию с устойчивым job ID."""
        await self.scheduler(
            ScheduleScheduledJobCommand(
                tenant_id,
                IMPORT_JOB,
                {"preparation_id": str(preparation_id), "sequence": sequence},
                now,
                uuid5(preparation_id, "step:" + str(sequence)),
            )
        )

    async def cleanup(
        self, tenant_id: UUID, preparation_id: UUID, at: datetime
    ) -> None:
        """Планирует очистку; повтор того же срока не создаёт второе задание."""
        await self.scheduler(
            ScheduleScheduledJobCommand(
                tenant_id,
                IMPORT_CLEANUP_JOB,
                {"preparation_id": str(preparation_id)},
                at,
                uuid5(preparation_id, "cleanup:" + at.isoformat()),
            )
        )

    async def content_update(
        self, tenant_id: UUID, run_id: UUID, sequence: int, now: datetime
    ) -> None:
        """Планирует шаг контентного обновления в транзакции его корня."""
        await self.scheduler(
            ScheduleScheduledJobCommand(
                tenant_id,
                CONTENT_UPDATE_JOB,
                {"run_id": str(run_id), "sequence": sequence},
                now,
                uuid5(run_id, "content:" + str(sequence)),
            )
        )
