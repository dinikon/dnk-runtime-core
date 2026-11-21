from src.modules.inventory.application.stock_document.read_service import (
    ReceiptDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.query import (
    ListReceiptDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.dto import (
    ListReceiptDocumentsResultDTO,
)


class ListReceiptDocumentsHandler:
    """Выполняет отдельный сценарий чтения поступлений."""

    def __init__(self, reader: ReceiptDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: ListReceiptDocumentsQuery
    ) -> ListReceiptDocumentsResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.list(query)
