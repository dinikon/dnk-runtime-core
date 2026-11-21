from dataclasses import replace

from src.modules.inventory.application.stock_location.port.query_repository import (
    StockLocationQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.query import (
    ListStockLocationsQuery,
)
from src.modules.inventory.application.stock_location.query.list_stock_locations.dto import (
    ListStockLocationsResultDTO,
)
from src.modules.inventory.domain.warehouse.error import WarehouseNotFoundError


class ListStockLocationsHandler:
    """Читает страницу адресов существующего склада через порт проекций."""

    def __init__(self, repository: StockLocationQueryRepositoryProtocol) -> None:
        """Принимает read-порт без сессии и управления транзакцией."""
        self._repository = repository

    async def execute(
        self, query: ListStockLocationsQuery
    ) -> ListStockLocationsResultDTO:
        """Различает отсутствующий склад и пустую страницу, нормализует пробелы поиска."""
        if not await self._repository.warehouse_exists(query.warehouse_id):
            raise WarehouseNotFoundError("Склад не найден.")
        search = query.search.strip() if query.search is not None else None
        return await self._repository.list(replace(query, search=search or None))
