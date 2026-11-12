from src.modules.catalog.application.catalog_item.query.find_inventory_item_usage.handler import (
    FindInventoryItemUsageHandler,
)
from src.modules.catalog.application.catalog_item.query.find_inventory_item_usage.query import (
    FindInventoryItemUsageQuery,
)
from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


class CatalogInventoryItemUsage:
    """Читает использование через публичный сценарий Catalog, не его ORM."""

    def __init__(self, reader: FindInventoryItemUsageHandler) -> None:
        """Принимает публичный reader на той же сессии внешнего UoW."""
        self._reader = reader

    async def get(self, identifier: InventoryItemIdVO) -> InventoryItemDeletionUsage:
        """Возвращает доменному правилу Inventory только необходимый факт."""
        result = await self._reader.execute(
            FindInventoryItemUsageQuery(identifier.uuid)
        )
        return InventoryItemDeletionUsage(result.in_use)
