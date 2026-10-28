"""Адаптер публикаций к существующему Shared Jobs."""

from datetime import datetime
from uuid import UUID

from src.modules.channels.application.sync_run.port.jobs import SyncJob
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob

JOB_TYPE = "channels.sync_publications"


class SharedPublicationSyncJobs:
    """Не создаёт собственной очереди, retry или механизма lease."""

    def __init__(self, repository: ScheduledJobRepositoryProtocol) -> None:
        """Получает repository общей сессии UoW."""
        self.repository = repository

    async def schedule(self, job: SyncJob, now: datetime) -> None:
        """Сохраняет только идентификаторы и ревизию доступа."""
        await self.repository.schedule_once(
            ScheduledJob(
                job.job_id,
                job.tenant_id,
                JOB_TYPE,
                {
                    "tenant_id": str(job.tenant_id),
                    "channel_id": str(job.channel_id),
                    "connection_id": str(job.connection_id),
                    "run_id": str(job.run_id),
                    "job_id": str(job.job_id),
                    "config_revision": job.config_revision,
                },
                now,
                "scheduled",
                0,
                None,
                None,
                now,
                now,
            )
        )

    async def cancel(self, tenant_id: UUID, run_id: UUID, now: datetime) -> None:
        """Отменяет все неоконченные шаги конкретного запуска."""
        await self.repository.cancel_matching(
            tenant_id=tenant_id,
            job_type=JOB_TYPE,
            payload_contains={"run_id": str(run_id)},
            canceled_at=now,
        )

    async def active(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Проверяет наличие действующего задания."""
        return job_id not in await self.repository.terminal_or_missing(
            tenant_id=tenant_id, job_ids=[job_id]
        )

    async def owns(
        self, job: SyncJob, lock_token: str, *, for_update: bool = False
    ) -> bool:
        """Выполняет fencing непосредственно перед применением страницы."""
        return await self.repository.owns_current_lease(
            job_id=job.job_id,
            tenant_id=job.tenant_id,
            lock_token=lock_token,
            for_update=for_update,
        )
