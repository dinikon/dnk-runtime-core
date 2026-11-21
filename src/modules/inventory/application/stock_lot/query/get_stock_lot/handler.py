from src.modules.inventory.application.stock_lot.port.query_repository import (
    StockLotQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.dto import (
    GetStockLotResultDTO,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.query import (
    GetStockLotQuery,
)
from src.modules.inventory.domain.stock_lot.error import StockLotNotFoundError


class GetStockLotHandler:
    """Читает карточку партии без проверки текущих настроек прослеживаемости SKU."""

    def __init__(self, repository: StockLotQueryRepositoryProtocol) -> None:
        """Принимает порт чтения проекций текущего tenant."""
        self._repository = repository

    async def execute(self, query: GetStockLotQuery) -> GetStockLotResultDTO:
        """Возвращает карточку либо ошибку отсутствия внутри выбранного SKU."""
        result = await self._repository.get_details(query)
        if result is None:
            raise StockLotNotFoundError("Партия не найдена в указанном SKU.")
        return result
