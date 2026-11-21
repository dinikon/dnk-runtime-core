from src.modules.inventory.application.stock_document.port.issue_facts import (
    IssueFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.prepare_issue.query import (
    PrepareIssueQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_issue.dto import (
    PrepareIssueResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class PrepareIssueHandler:
    """Читает подготовку формы через специализированную проекцию."""

    def __init__(self, repository: IssueFactsQueryPort) -> None:
        """Принимает read-порт общей tenant-сессии."""
        self._repository = repository

    async def execute(self, query: PrepareIssueQuery) -> PrepareIssueResultDTO:
        """Возвращает текущую версию и остатки плана либо сообщает об отсутствии документа."""
        result = await self._repository.prepare(query)
        if result is None:
            raise StockDocumentNotFoundError("Расход не найдено.")
        return result
