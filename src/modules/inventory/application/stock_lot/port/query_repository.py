from typing import Protocol

from src.modules.inventory.application.stock_lot.query.get_stock_lot.dto import (
    GetStockLotResultDTO,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.query import (
    GetStockLotQuery,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.dto import (
    ListStockLotsResultDTO,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.query import (
    ListStockLotsQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)


class StockLotQueryRepositoryProtocol(Protocol):
    """Определяет чтение конкретных проекций партий в tenant-контексте."""

    async def item_exists(self, identifier: InventoryItemIdVO) -> bool:
        """Проверяет наличие владельца без загрузки его агрегата."""
        ...

    async def get_details(self, query: GetStockLotQuery) -> GetStockLotResultDTO | None:
        """Читает партию только внутри указанного SKU."""
        ...

    async def list(self, query: ListStockLotsQuery) -> ListStockLotsResultDTO:
        """Возвращает отфильтрованную страницу и общее число совпадений."""
        ...
