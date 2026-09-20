from datetime import datetime
from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.price_lists.domain.price_list.value_object import PriceListIdVO
from src.modules.price_lists.domain.sync_run.entity import SyncRun


class SyncRunRepository(Protocol):
    """Порт результатов и прогресса синхронизации."""

    async def skip_running(self, tenant_id: EntityIdVO, price_list_id: PriceListIdVO, now: datetime) -> None:
        """Завершает отозванные lifecycle-переходом запуски."""
        ...

    async def find_by_job(
        self, tenant_id: EntityIdVO, price_list_id: PriceListIdVO, job_id: EntityIdVO
    ) -> SyncRun | None: ...
    async def add(self, tenant_id: EntityIdVO, run: SyncRun) -> None: ...
    async def save(self, tenant_id: EntityIdVO, run: SyncRun) -> None: ...


__all__ = ["SyncRunRepository"]
