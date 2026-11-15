from typing import Protocol
from src.modules.inventory.application.stock_document.query.get_receipt_document.query import (
    GetReceiptDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_receipt_document.dto import (
    GetReceiptDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.query import (
    ListReceiptDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_documents.dto import (
    ListReceiptDocumentsResultDTO,
)


class ReceiptDocumentQueryRepositoryProtocol(Protocol):
    """Определяет отдельный read-side поступлений."""

    async def get(
        self, query: GetReceiptDocumentQuery
    ) -> GetReceiptDocumentResultDTO | None:
        """Проецирует карточку и строки без восстановления Domain."""
        ...

    async def list(
        self, query: ListReceiptDocumentsQuery
    ) -> ListReceiptDocumentsResultDTO:
        """Читает страницу и total по одним фильтрам."""
        ...
