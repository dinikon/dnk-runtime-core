from typing import Protocol

from src.modules.inventory.application.stock_serial.query.get_stock_serial.dto import (
    GetStockSerialResultDTO,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.query import (
    GetStockSerialQuery,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.dto import (
    ListStockSerialsResultDTO,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.query import (
    ListStockSerialsQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


class StockSerialQueryRepositoryProtocol(Protocol):
    """Определяет чтение конкретных проекций серийных экземпляров в tenant-контексте."""

    async def item_exists(self, identifier: InventoryItemIdVO) -> bool:
        """Проверяет наличие владельца без загрузки его агрегата."""
        ...

    async def get_details(
        self, query: GetStockSerialQuery
    ) -> GetStockSerialResultDTO | None:
        """Читает экземпляр только внутри указанного SKU."""
        ...

    async def list(self, query: ListStockSerialsQuery) -> ListStockSerialsResultDTO:
        """Возвращает отфильтрованную страницу и общее число совпадений."""
        ...
