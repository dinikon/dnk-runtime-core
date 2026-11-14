from dataclasses import replace

from src.modules.inventory.application.stock_lot.port.query_repository import (
    StockLotQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.dto import (
    ListStockLotsResultDTO,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.query import (
    ListStockLotsQuery,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError


class ListStockLotsHandler:
    """Различает отсутствующий SKU и пустую страницу его партий."""

    def __init__(self, repository: StockLotQueryRepositoryProtocol) -> None:
        """Принимает read-порт общей tenant-транзакции."""
        self._repository = repository

    async def execute(self, query: ListStockLotsQuery) -> ListStockLotsResultDTO:
        """Проверяет владельца и нормализует поиск без изменения регистра номера."""
        if not await self._repository.item_exists(query.inventory_item_id):
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        search = query.search.strip() if query.search is not None else None
        return await self._repository.list(replace(query, search=search or None))
