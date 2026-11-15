from typing import Protocol
from uuid import UUID


class PhysicalInventoryUsagePort(Protocol):
    """Передаёт факты учётного использования без SQL и физических агрегатов."""

    async def item_has_history(self, identifier: UUID) -> bool:
        """Проверяет наличие фактической истории SKU."""
        ...

    async def serial_has_history(self, identifier: UUID) -> bool:
        """Проверяет наличие фактической истории конкретного экземпляра."""
        ...
