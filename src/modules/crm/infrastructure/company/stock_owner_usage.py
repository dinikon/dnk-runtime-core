from uuid import UUID
from src.modules.inventory.application.stock_document.port.owner_usage import (
    InventoryStockOwnerUsageProtocol,
)


class InventoryCompanyStockOwnerUsage:
    """Адаптирует публичный контракт Inventory без чужих ORM-моделей."""

    def __init__(self, usage: InventoryStockOwnerUsageProtocol) -> None:
        """Принимает публичный порт одной общей транзакции."""
        self._usage = usage

    async def is_used(self, identifier: UUID) -> bool:
        """Не исключает черновики и отменённые документы."""
        return await self._usage.is_owner_used(identifier)
