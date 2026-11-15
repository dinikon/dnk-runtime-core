from src.modules.inventory.application.stock_document.port.return_facts import (
    ReturnFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_return_destinations.query import (
    ListReturnDestinationsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_destinations.dto import (
    ListReturnDestinationsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class ListReturnDestinationsHandler:
    """Организует поиск адресов назначения через порт проекций."""

    def __init__(self, repository: ReturnFactsQueryPort) -> None:
        """Получает порт чтения на общей tenant-сессии."""
        self._repository = repository

    async def execute(
        self, query: ListReturnDestinationsQuery
    ) -> ListReturnDestinationsResultDTO:
        """Отличает отсутствующий документ от пустой страницы адресов."""
        result = await self._repository.destinations(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ возврата не найден.")
        return result
