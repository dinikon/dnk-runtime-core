from src.modules.inventory.domain.inventory_item.accounting_usage import (
    InventoryItemAccountingUsage,
)
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

    async def item_state(self, identifier: UUID) -> InventoryItemAccountingUsage:
        """Возвращает все различные количества и даты партий положительных остатков."""
        ...

    async def lot_has_positive_stock(self, identifier: UUID) -> bool:
        """Проверяет физический запас партии, включая связанные серийные экземпляры."""
        ...
