from src.modules.inventory.application.stock_document.write_off_read_service import (
    WriteOffDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.query import (
    ListWriteOffDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.dto import (
    ListWriteOffDocumentsResultDTO,
)


class ListWriteOffDocumentsHandler:
    """Выполняет отдельный сценарий чтения списаний."""

    def __init__(self, reader: WriteOffDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: ListWriteOffDocumentsQuery
    ) -> ListWriteOffDocumentsResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.list(query)
