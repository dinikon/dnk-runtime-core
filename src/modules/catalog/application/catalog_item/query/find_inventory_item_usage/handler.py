from src.modules.catalog.application.catalog_item.port.sku import CatalogItemSkuPort
from src.modules.catalog.application.catalog_item.query.find_inventory_item_usage.dto import (
    FindInventoryItemUsageResultDTO,
)
from src.modules.catalog.application.catalog_item.query.find_inventory_item_usage.query import (
    FindInventoryItemUsageQuery,
)


class FindInventoryItemUsageHandler:
    """Предоставляет публичное чтение использования без загрузки агрегатов."""

    def __init__(self, links: CatalogItemSkuPort) -> None:
        """Принимает read-порт связей текущего tenant."""
        self._links = links

    async def execute(
        self, query: FindInventoryItemUsageQuery
    ) -> FindInventoryItemUsageResultDTO:
        """Не исключает архивные или черновые карточки из проверки."""
        return FindInventoryItemUsageResultDTO(
            await self._links.owner(query.inventory_item_id) is not None
        )
