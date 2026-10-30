from datetime import datetime
from uuid import UUID

from src.modules.channels.domain.stock_sync.aggregate import StockSync
from src.modules.shared.domain.jobs.scheduled_job import ScheduledJob
from src.modules.shared.application.jobs.scheduled_job_repository_protocol import (
    ScheduledJobRepositoryProtocol,
)

JOB_TYPE = "channels.sync_stock"
CATALOG_EVENT_JOB_TYPE = "catalog.stock_changed"


class SharedStockJobs:
    """Использует существующие retry, lease и восстановление Shared Jobs."""

    def __init__(self, jobs: ScheduledJobRepositoryProtocol) -> None:
        """Получает repository того же UoW."""
        self.jobs = jobs

    async def schedule(
        self, *, tenant_id: UUID, channel_id: UUID, state: StockSync, now: datetime
    ) -> None:
        """Envelope содержит идентификаторы без настроек, количества и credentials."""
        await self.jobs.schedule_once(
            ScheduledJob(
                state.operation_id.uuid,
                tenant_id,
                JOB_TYPE,
                {
                    "channel_id": str(channel_id),
                    "publication_id": str(state.publication_id.uuid),
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

    async def cancel_channel(
        self, *, tenant_id: UUID, channel_id: UUID, now: datetime
    ) -> None:
        """Отменяет ожидающие и активные задания конкретного канала."""
        await self.jobs.cancel_matching(
            tenant_id=tenant_id,
            job_type=JOB_TYPE,
            payload_contains={"channel_id": str(channel_id)},
            canceled_at=now,
        )

    async def active(self, *, tenant_id: UUID, job_id: UUID) -> bool:
        """Позволяет повторно запустить потерянное задание."""
        return job_id not in await self.jobs.terminal_or_missing(
            tenant_id=tenant_id, job_ids=[job_id]
        )

    async def owns(
        self,
        *,
        tenant_id: UUID,
        job_id: UUID,
        lock_token: str,
        for_update: bool = False,
    ) -> bool:
        """Проверяет действующее поколение lease."""
        return await self.jobs.owns_current_lease(
            job_id=job_id,
            tenant_id=tenant_id,
            lock_token=lock_token,
            for_update=for_update,
        )
