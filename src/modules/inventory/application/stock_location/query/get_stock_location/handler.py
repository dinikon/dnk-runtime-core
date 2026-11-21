from src.modules.inventory.application.stock_location.port.query_repository import (
    StockLocationQueryRepositoryProtocol,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.query import (
    GetStockLocationQuery,
)
from src.modules.inventory.application.stock_location.query.get_stock_location.dto import (
    GetStockLocationResultDTO,
)
from src.modules.inventory.domain.stock_location.error import StockLocationNotFoundError


class GetStockLocationHandler:
    """Читает проекцию карточки внутри выбранного склада."""

    def __init__(self, repository: StockLocationQueryRepositoryProtocol) -> None:
        """Принимает порт проекций текущего tenant."""
        self._repository = repository

    async def execute(self, query: GetStockLocationQuery) -> GetStockLocationResultDTO:
        """Возвращает DTO либо предметную ошибку отсутствующей локации."""
        result = await self._repository.get_details(query)
        if result is None:
            raise StockLocationNotFoundError("Локация не найдена в указанном складе.")
        return result
