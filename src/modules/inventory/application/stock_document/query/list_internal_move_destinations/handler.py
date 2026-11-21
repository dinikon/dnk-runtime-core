from src.modules.inventory.application.stock_document.port.internal_move_facts import (
    InternalMoveFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.query import (
    ListInternalMoveDestinationsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.dto import (
    ListInternalMoveDestinationsResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class ListInternalMoveDestinationsHandler:
    """Организует поиск адресов назначения через порт проекций."""

    def __init__(self, repository: InternalMoveFactsQueryPort) -> None:
        """Получает порт чтения на общей tenant-сессии."""
        self._repository = repository

    async def execute(
        self, query: ListInternalMoveDestinationsQuery
    ) -> ListInternalMoveDestinationsResultDTO:
        """Отличает отсутствующий документ от пустой страницы адресов."""
        result = await self._repository.destinations(query)
        if result is None:
            raise StockDocumentNotFoundError("Документ перемещения не найден.")
        return result
