from datetime import datetime
from uuid import UUID

from src.modules.channels.domain.content_delivery.aggregate import ContentDelivery
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob

JOB_TYPE = "channels.deliver_content"


class SharedContentDeliveryJobs:
    """Связывает поколения целей с существующими Shared Jobs."""

    def __init__(self, jobs: ScheduledJobRepositoryProtocol) -> None:
        """Принимает repository той же сессии UoW."""
        self._jobs = jobs

    async def schedule(
        self, *, tenant_id: UUID, delivery: ContentDelivery, now: datetime
    ) -> None:
        """Не помещает контент, URL или credentials в envelope задания."""
        await self._jobs.schedule_once(
            ScheduledJob(
                delivery.current_job_id.uuid,
                tenant_id,
                JOB_TYPE,
                {
                    "channel_id": str(delivery.requested_context.channel_id.uuid),
                    "group_id": str(delivery.requested_context.group_id.uuid),
                    "representation_id": str(delivery.representation_id.uuid),
                    "publication_id": str(delivery.publication_id.uuid),
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

    async def owns(
        self,
        *,
        tenant_id: UUID,
        job_id: UUID,
        lock_token: str,
        for_update: bool = False,
    ) -> bool:
        """Проверяет lease на той же сессии, что изменение цели и media."""
        return await self._jobs.owns_current_lease(
            job_id=job_id,
            tenant_id=tenant_id,
            lock_token=lock_token,
            for_update=for_update,
        )

    async def active(self, *, tenant_id: UUID, job_id: UUID) -> bool:
        """Позволяет Console предложить восстановление утраченной работы."""
        return job_id not in await self._jobs.terminal_or_missing(
            tenant_id=tenant_id, job_ids=[job_id]
        )

    async def cancel_channel(
        self, *, tenant_id: UUID, channel_id: UUID, now: datetime
    ) -> None:
        """Отзывает lease всех работ удаляемого канала без внешнего вызова."""
        await self._jobs.cancel_matching(
            tenant_id=tenant_id,
            job_type=JOB_TYPE,
            payload_contains={"channel_id": str(channel_id)},
            canceled_at=now,
        )
