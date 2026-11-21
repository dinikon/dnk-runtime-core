from src.modules.inventory.application.stock_document.issue_read_service import (
    IssueDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_issue_document.query import (
    GetIssueDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_issue_document.dto import (
    GetIssueDocumentResultDTO,
)


class GetIssueDocumentHandler:
    """Выполняет отдельный сценарий чтения расходов."""

    def __init__(self, reader: IssueDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(self, query: GetIssueDocumentQuery) -> GetIssueDocumentResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.get(query)
