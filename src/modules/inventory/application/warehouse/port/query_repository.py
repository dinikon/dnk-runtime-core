from typing import Protocol

from src.modules.inventory.application.warehouse.query.get_warehouse.query import (
    GetWarehouseQuery,
)
from src.modules.inventory.application.warehouse.query.get_warehouse.dto import (
    GetWarehouseResultDTO,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.query import (
    ListWarehousesQuery,
)
from src.modules.inventory.application.warehouse.query.list_warehouses.dto import (
    ListWarehousesResultDTO,
)


class WarehouseQueryRepositoryProtocol(Protocol):
    """Определяет чтение проекций складов в текущем tenant."""

    async def get_details(
        self, query: GetWarehouseQuery
    ) -> GetWarehouseResultDTO | None:
        """Возвращает карточку или None без восстановления агрегата."""
        ...

    async def list(self, query: ListWarehousesQuery) -> ListWarehousesResultDTO:
        """Возвращает страницу и total по одному набору фильтров."""
        ...
