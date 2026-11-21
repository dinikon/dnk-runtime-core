from src.modules.inventory.application.stock_document.port.issue_facts import (
    IssueFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_issue_sources.query import (
    ListIssueSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_issue_sources.dto import (
    ListIssueSourcesResultDTO,
)
from src.modules.inventory.domain.stock_document.error import (
    StockDocumentLineNotFoundError,
)


class ListIssueSourcesHandler:
    """Читает только проекции источников через Application-порт."""

    def __init__(self, repository: IssueFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(self, query: ListIssueSourcesQuery) -> ListIssueSourcesResultDTO:
        """Отличает пустой физический запас от отсутствующего документа или строки."""
        result = await self._repository.sources(query)
        if result is None:
            raise StockDocumentLineNotFoundError("Строка расхода не найдена.")
        return result
