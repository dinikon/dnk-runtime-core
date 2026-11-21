from typing import Protocol

from src.modules.inventory.application.inventory_item.query.get_inventory_item.dto import (
    GetInventoryItemResultDTO,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.query import (
    GetInventoryItemQuery,
)

from src.modules.inventory.application.inventory_item.query.list_inventory_items.dto import (
    ListInventoryItemsResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.query import (
    ListInventoryItemsQuery,
)


class InventoryItemQueryRepositoryProtocol(Protocol):
    """Определяет чтение проекций в tenant-контексте внешней сборки."""

    async def get_details(
        self, query: GetInventoryItemQuery
    ) -> GetInventoryItemResultDTO | None:
        """Возвращает карточку текущего tenant либо None."""
        ...

    async def list(self, query: ListInventoryItemsQuery) -> ListInventoryItemsResultDTO:
        """Возвращает страницу и total по одному набору фильтров."""
        ...
