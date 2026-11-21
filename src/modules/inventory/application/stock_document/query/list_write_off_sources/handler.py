from src.modules.inventory.application.stock_document.port.write_off_facts import (
    WriteOffFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_write_off_sources.query import (
    ListWriteOffSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_sources.dto import (
    ListWriteOffSourcesResultDTO,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


class ListWriteOffSourcesHandler:
    """Читает только проекции источников через Application-порт."""

    def __init__(self, repository: WriteOffFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListWriteOffSourcesQuery
    ) -> ListWriteOffSourcesResultDTO:
        """Отличает пустой физический запас от отсутствующего документа или строки."""
        result = await self._repository.sources(query)
        if result is None:
            raise StockDocumentLineNotFoundError("Строка списания не найдена.")
        return result
