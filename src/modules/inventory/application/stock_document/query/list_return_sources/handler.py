from src.modules.inventory.application.stock_document.port.return_facts import (
    ReturnFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.query import (
    ListReturnSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.dto import (
    ListReturnSourcesResultDTO,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


class ListReturnSourcesHandler:
    """Читает только проекции источников через Application-порт."""

    def __init__(self, repository: ReturnFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListReturnSourcesQuery
    ) -> ListReturnSourcesResultDTO:
        """Отличает пустой физический запас от отсутствующего документа или строки."""
        result = await self._repository.sources(query)
        if result is None:
            raise StockDocumentLineNotFoundError("Строка возврата не найдена.")
        return result
