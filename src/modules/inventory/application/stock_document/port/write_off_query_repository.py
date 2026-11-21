from typing import Protocol
from src.modules.inventory.application.stock_document.query.get_write_off_document.query import (
    GetWriteOffDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.dto import (
    GetWriteOffDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.query import (
    ListWriteOffDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_documents.dto import (
    ListWriteOffDocumentsResultDTO,
)


class WriteOffDocumentQueryRepositoryProtocol(Protocol):
    """Определяет отдельный read-side списаний."""

    async def get(
        self, query: GetWriteOffDocumentQuery
    ) -> GetWriteOffDocumentResultDTO | None:
        """Проецирует карточку и строки без восстановления Domain."""
        ...

    async def list(
        self, query: ListWriteOffDocumentsQuery
    ) -> ListWriteOffDocumentsResultDTO:
        """Читает страницу и total по одним фильтрам."""
        ...
