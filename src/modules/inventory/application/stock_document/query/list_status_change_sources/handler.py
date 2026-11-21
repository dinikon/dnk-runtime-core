from src.modules.inventory.application.stock_document.port.status_change_facts import (
    StatusChangeFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_status_change_sources.query import (
    ListStatusChangeSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_status_change_sources.dto import (
    ListStatusChangeSourcesResultDTO,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


class ListStatusChangeSourcesHandler:
    """Читает только проекции источников через Application-порт."""

    def __init__(self, repository: StatusChangeFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListStatusChangeSourcesQuery
    ) -> ListStatusChangeSourcesResultDTO:
        """Отличает пустой физический запас от отсутствующего документа или строки."""
        result = await self._repository.sources(query)
        if result is None:
            raise StockDocumentLineNotFoundError(
                "Строка изменения состояния не найдена."
            )
        return result
