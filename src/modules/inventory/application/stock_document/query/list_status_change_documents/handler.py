from src.modules.inventory.application.stock_document.status_change_read_service import (
    StatusChangeDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.query import (
    ListStatusChangeDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.dto import (
    ListStatusChangeDocumentsResultDTO,
)


class ListStatusChangeDocumentsHandler:
    """Выполняет отдельный сценарий чтения изменений состояния."""

    def __init__(self, reader: StatusChangeDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: ListStatusChangeDocumentsQuery
    ) -> ListStatusChangeDocumentsResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.list(query)
