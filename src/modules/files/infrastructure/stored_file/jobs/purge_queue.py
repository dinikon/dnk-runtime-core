from datetime import datetime
from uuid import UUID
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_use_case import (
    ScheduleScheduledJobUseCase,
)
from src.modules.shared.application.jobs.schedule_scheduled_job_command import (
    ScheduleScheduledJobCommand,
)


class ScheduledFilePurgeQueue:
    """Адаптирует Application contracts shared jobs к файловому purge без отдельного UoW."""

    def __init__(
        self,
        scheduler: ScheduleScheduledJobUseCase,
        repository: ScheduledJobRepositoryProtocol,
    ) -> None:
        """Принимает scheduler и repository, собранные на сессии файлового UoW."""
        self._scheduler, self._repository = scheduler, repository

    async def schedule(
        self, tenant_id: UUID, file_id: UUID, job_id: UUID, run_at: datetime
    ) -> None:
        """Планирует идемпотентную files.purge job только с безопасными ID."""
        await self._scheduler(
            ScheduleScheduledJobCommand(
                tenant_id=tenant_id,
                job_id=job_id,
                job_type="files.purge",
                payload={
                    "tenant_id": str(tenant_id),
                    "file_id": str(file_id),
                    "job_id": str(job_id),
                },
                run_at=run_at,
            )
        )

    async def schedule_cleanup(
        self,
        tenant_id: UUID,
        job_id: UUID,
        cutoff: datetime,
        after_id: UUID | None = None,
        batch_size: int = 100,
    ) -> None:
        """Сохраняет scan/continuation с неизменным cutoff в общей транзакции."""
        await self._scheduler(
            ScheduleScheduledJobCommand(
                tenant_id=tenant_id,
                job_id=job_id,
                job_type="files.trash.cleanup",
                payload={
                    "cutoff": cutoff.isoformat(),
                    "after_id": str(after_id) if after_id else None,
                    "batch_size": batch_size,
                },
                run_at=cutoff,
            )
        )

    async def terminal_or_missing(
        self, tenant_id: UUID, job_ids: tuple[UUID, ...]
    ) -> frozenset[UUID]:
        """Читает статусы recovery через ограниченный Application-контракт shared jobs."""
        if len(job_ids) > 100:
            raise ValueError("Purge recovery batch exceeds 100 IDs.")
        return frozenset(
            await self._repository.terminal_or_missing(
                tenant_id=tenant_id, job_ids=list(job_ids)
            )
        )
