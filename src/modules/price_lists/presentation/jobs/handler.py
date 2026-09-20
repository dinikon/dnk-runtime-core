from datetime import datetime
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.jobs import ScheduledJob
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.application.sync_run.command.synchronize_price_list_command import (
    SynchronizePriceListCommand,
)
from src.modules.price_lists.application.sync_run.command.cleanup_price_list_command import (
    CleanupPriceListCommand,
)
from src.modules.price_lists.application.sync_run.use_case.synchronize_price_list import (
    SynchronizePriceListUseCase,
)
from src.modules.price_lists.application.sync_run.use_case.cleanup_price_list import (
    CleanupPriceListUseCase,
)


class PriceListSyncJobHandler:
    """Преобразует scheduled-job envelope в application command."""

    def __init__(self, use_case: SynchronizePriceListUseCase):
        self.use_case = use_case

    async def handle(self, job: ScheduledJob) -> None:
        payload = job.payload
        revision = payload.get("schedule_revision")
        trigger = payload.get("trigger") or "cron"
        if (
            type(revision) is not int
            or revision < 1
            or trigger not in ("initial", "cron", "manual", "retry")
        ):
            raise ValueError("Invalid price-list job payload.")
        planned_at = (
            datetime.fromisoformat(payload["planned_at"])
            if payload.get("planned_at")
            else job.run_at
        )
        if planned_at.tzinfo is None:
            raise ValueError("Planned timestamp must include timezone.")
        await self.use_case(
            SynchronizePriceListCommand(
                EntityIdVO.from_value(job.tenant_id),
                PriceListIdVO.from_value(payload["price_list_id"]),
                EntityIdVO.from_value(job.id),
                revision,
                trigger,
                planned_at,
                job.lock_token or "",
            )
        )


class PriceListCleanupJobHandler:
    """Адаптирует maintenance job к application сценарию."""

    def __init__(self, use_case: CleanupPriceListUseCase):
        self.use_case = use_case

    async def handle(self, job: ScheduledJob) -> None:
        await self.use_case(
            CleanupPriceListCommand(
                EntityIdVO.from_value(job.tenant_id),
                EntityIdVO.from_value(job.id),
                job.lock_token or "",
            )
        )


__all__ = ["PriceListSyncJobHandler", "PriceListCleanupJobHandler"]
