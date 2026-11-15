from typing import Protocol
from src.modules.inventory.application.stock_document.query.get_issue_document.query import (
    GetIssueDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_issue_document.dto import (
    GetIssueDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.query import (
    ListIssueDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_issue_documents.dto import (
    ListIssueDocumentsResultDTO,
)


class IssueDocumentQueryRepositoryProtocol(Protocol):
    """Определяет отдельный read-side расходов."""

    async def get(
        self, query: GetIssueDocumentQuery
    ) -> GetIssueDocumentResultDTO | None:
        """Проецирует карточку и строки без восстановления Domain."""
        ...

    async def list(self, query: ListIssueDocumentsQuery) -> ListIssueDocumentsResultDTO:
        """Читает страницу и total по одним фильтрам."""
        ...
