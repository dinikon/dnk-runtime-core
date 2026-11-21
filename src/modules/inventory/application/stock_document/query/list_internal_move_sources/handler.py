from src.modules.inventory.application.stock_document.port.internal_move_facts import (
    InternalMoveFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.query import (
    ListInternalMoveSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.dto import (
    ListInternalMoveSourcesResultDTO,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


class ListInternalMoveSourcesHandler:
    """Читает только проекции источников через Application-порт."""

    def __init__(self, repository: InternalMoveFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListInternalMoveSourcesQuery
    ) -> ListInternalMoveSourcesResultDTO:
        """Отличает пустой физический запас от отсутствующего документа или строки."""
        result = await self._repository.sources(query)
        if result is None:
            raise StockDocumentLineNotFoundError("Строка перемещения не найдена.")
        return result
