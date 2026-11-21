from src.modules.inventory.application.stock_document.issue_read_service import (
    IssueDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.query import (
    ListIssueDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.dto import (
    ListIssueDocumentsResultDTO,
)


class ListIssueDocumentsHandler:
    """Выполняет отдельный сценарий чтения расходов."""

    def __init__(self, reader: IssueDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: ListIssueDocumentsQuery
    ) -> ListIssueDocumentsResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.list(query)
