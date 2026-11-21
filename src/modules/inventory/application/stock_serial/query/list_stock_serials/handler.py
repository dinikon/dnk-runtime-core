from dataclasses import replace

from src.modules.inventory.application.stock_serial.port.query_repository import (
    StockSerialQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.dto import (
    ListStockSerialsResultDTO,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.query import (
    ListStockSerialsQuery,
)
from src.modules.inventory.domain.inventory_item.error import InventoryItemNotFoundError


class ListStockSerialsHandler:
    """Различает отсутствующий SKU и пустую страницу его серийных экземпляров."""

    def __init__(self, repository: StockSerialQueryRepositoryProtocol) -> None:
        """Принимает read-порт общей tenant-транзакции."""
        self._repository = repository

    async def execute(self, query: ListStockSerialsQuery) -> ListStockSerialsResultDTO:
        """Проверяет владельца и нормализует поиск без изменения регистра номера."""
        if not await self._repository.item_exists(query.inventory_item_id):
            raise InventoryItemNotFoundError("Складская позиция не найдена.")
        search = query.search.strip() if query.search is not None else None
        return await self._repository.list(replace(query, search=search or None))
