from datetime import datetime
from uuid import UUID

from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob

JOB_TYPE = "channels.apply_content_feed"


class SharedFeedImportJobs:
    """Связывает состояние операции с надёжными заданиями существующего Shared слоя."""

    def __init__(self, jobs: ScheduledJobRepositoryProtocol) -> None:
        """Получает repository общей транзакции ContentFeed."""
        self._jobs = jobs

    async def schedule(
        self,
        *,
        tenant_id: UUID,
        channel_id: UUID,
        feed_id: UUID,
        operation_id: UUID,
        job_id: UUID,
        run_at: datetime,
    ) -> None:
        """Сохраняет идентификаторы без URL, контента и credentials."""
        await self._jobs.schedule_once(
            ScheduledJob(
                job_id,
                tenant_id,
                JOB_TYPE,
                {
                    "channel_id": str(channel_id),
                    "feed_id": str(feed_id),
                    "operation_id": str(operation_id),
                },
                run_at,
                "scheduled",
                0,
                None,
                None,
                run_at,
                run_at,
            )
        )

    async def owns(self, *, tenant_id: UUID, job_id: UUID, lock_token: str) -> bool:
        """Блокирует актуальную lease на время фиксации бизнес-результата."""
        return await self._jobs.owns_current_lease(
            job_id=job_id, tenant_id=tenant_id, lock_token=lock_token, for_update=True
        )

    async def active(self, *, tenant_id: UUID, job_id: UUID) -> bool:
        """Позволяет предложить восстановление утраченного этапа."""
        return job_id not in await self._jobs.terminal_or_missing(
            tenant_id=tenant_id, job_ids=[job_id]
        )

    async def cancel_channel(
        self, *, tenant_id: UUID, channel_id: UUID, now: datetime
    ) -> None:
        """Отменяет оставшиеся задания после доменной проверки возможности удаления."""
        await self._jobs.cancel_matching(
            tenant_id=tenant_id,
            job_type=JOB_TYPE,
            payload_contains={"channel_id": str(channel_id)},
            canceled_at=now,
        )
