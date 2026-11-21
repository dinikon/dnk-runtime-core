from typing import Protocol

from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


class InventoryItemUsagePort(Protocol):
    """Определяет чтение использования позиции без зависимости от чужой модели."""

    async def get(self, identifier: InventoryItemIdVO) -> InventoryItemDeletionUsage:
        """Возвращает снимок использования в текущем tenant и транзакции."""
        ...
