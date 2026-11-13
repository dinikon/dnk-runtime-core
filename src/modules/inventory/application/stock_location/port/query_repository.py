from typing import Protocol

from src.modules.inventory.domain.warehouse.value_object.identifier import WarehouseIdVO
from src.modules.inventory.application.stock_location.query.get_stock_location.query import (
    GetStockLocationQuery,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.dto import (
    GetStockLocationResultDTO,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.query import (
    ListStockLocationsQuery,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.dto import (
    ListStockLocationsResultDTO,
)


class StockLocationQueryRepositoryProtocol(Protocol):
    """Определяет чтение проекций локаций без восстановления агрегатов."""

    async def warehouse_exists(self, identifier: WarehouseIdVO) -> bool:
        """Отличает отсутствующий склад от пустого результата его списка."""
        ...

    async def get_details(
        self, query: GetStockLocationQuery
    ) -> GetStockLocationResultDTO | None:
        """Возвращает карточку только внутри указанного склада либо None."""
        ...

    async def list(self, query: ListStockLocationsQuery) -> ListStockLocationsResultDTO:
        """Возвращает страницу и общее число по тем же фильтрам."""
        ...
