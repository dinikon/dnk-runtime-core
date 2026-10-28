from datetime import datetime
from uuid import UUID

from src.modules.channels.application.channel.port.jobs import VerificationJob
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob

JOB_TYPE = "channels.verify_connection"


class SharedVerificationJobs:
    """Адаптирует узкий порт Channels к существующему Shared Jobs."""

    def __init__(self, repository: ScheduledJobRepositoryProtocol) -> None:
        """Принимает jobs repository той же сессии, что ChannelRepositoryProtocol."""
        self.repository = repository

    async def schedule(self, job: VerificationJob, now: datetime) -> None:
        """Записывает только идентификаторы и ревизию подключения."""
        await self.repository.schedule_once(
            ScheduledJob(
                job.job_id,
                job.tenant_id,
                JOB_TYPE,
                {
                    "tenant_id": str(job.tenant_id),
                    "channel_id": str(job.channel_id),
                    "connection_id": str(job.connection_id),
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

    async def cancel(self, tenant_id: UUID, channel_id: UUID, now: datetime) -> None:
        """Отменяет проверки данного Channel в пределах tenant."""
        await self.repository.cancel_matching(
            tenant_id=tenant_id,
            job_type=JOB_TYPE,
            payload_contains={"channel_id": str(channel_id)},
            canceled_at=now,
        )

    async def active(self, tenant_id: UUID, job_id: UUID) -> bool:
        """Проверяет, что текущее задание ещё может выполняться."""
        return job_id not in await self.inactive(tenant_id, [job_id])

    async def inactive(self, tenant_id: UUID, job_ids: list[UUID]) -> set[UUID]:
        """Получает terminal/missing задания одним запросом на страницу."""
        return await self.repository.terminal_or_missing(
            tenant_id=tenant_id, job_ids=job_ids
        )

    async def owns(
        self, job: VerificationJob, lock_token: str, *, for_update: bool = False
    ) -> bool:
        """Проверяет fencing lease по времени БД."""
        return await self.repository.owns_current_lease(
            job_id=job.job_id,
            tenant_id=job.tenant_id,
            lock_token=lock_token,
            for_update=for_update,
        )
