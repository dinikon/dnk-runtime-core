from src.modules.inventory.application.stock_document.return_read_service import (
    ReturnDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.query import (
    ListReturnDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.dto import (
    ListReturnDocumentsResultDTO,
)


class ListReturnDocumentsHandler:
    """Выполняет отдельный сценарий чтения изменений состояния."""

    def __init__(self, reader: ReturnDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: ListReturnDocumentsQuery
    ) -> ListReturnDocumentsResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.list(query)
