from src.modules.inventory.application.stock_serial.port.query_repository import (
    StockSerialQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.dto import (
    GetStockSerialResultDTO,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.query import (
    GetStockSerialQuery,
)
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError


class GetStockSerialHandler:
    """Читает карточку экземпляра без проверки текущих настроек прослеживаемости SKU."""

    def __init__(self, repository: StockSerialQueryRepositoryProtocol) -> None:
        """Принимает порт чтения проекций текущего tenant."""
        self._repository = repository

    async def execute(self, query: GetStockSerialQuery) -> GetStockSerialResultDTO:
        """Возвращает карточку либо ошибку отсутствия внутри выбранного SKU."""
        result = await self._repository.get_details(query)
        if result is None:
            raise StockSerialNotFoundError("Партия не найдена в указанном SKU.")
        return result
