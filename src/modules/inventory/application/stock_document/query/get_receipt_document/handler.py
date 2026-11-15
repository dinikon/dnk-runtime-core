from src.modules.inventory.application.stock_document.read_service import (
    ReceiptDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.query import (
    GetReceiptDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.dto import (
    GetReceiptDocumentResultDTO,
)


class GetReceiptDocumentHandler:
    """Выполняет отдельный сценарий чтения поступлений."""

    def __init__(self, reader: ReceiptDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: GetReceiptDocumentQuery
    ) -> GetReceiptDocumentResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.get(query)
