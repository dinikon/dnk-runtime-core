from typing import Protocol
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.query import (
    GetItemPackagingQuery,
)
from src.modules.inventory.application.inventory_item.query.get_item_packaging.dto import (
    GetItemPackagingResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.query import (
    ListItemPackagingsQuery,
)
from src.modules.inventory.application.inventory_item.query.list_item_packagings.dto import (
    ListItemPackagingsResultDTO,
)


class ItemPackagingQueryRepositoryProtocol(Protocol):
    """Определяет чтение проекций дочерних упаковок без восстановления агрегата."""

    async def item_exists(self, identifier: InventoryItemIdVO) -> bool:
        """Отличает отсутствующий товар от пустого списка его упаковок."""
        ...

    async def get_details(
        self, query: GetItemPackagingQuery
    ) -> GetItemPackagingResultDTO | None:
        """Возвращает упаковку только внутри указанного товара либо None."""
        ...

    async def list(self, query: ListItemPackagingsQuery) -> ListItemPackagingsResultDTO:
        """Возвращает страницу проекций с одинаковыми фильтрами total и items."""
        ...
