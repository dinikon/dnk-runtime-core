from typing import Protocol
from src.modules.inventory.application.stock_document.query.get_return_document.query import (
    GetReturnDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_return_document.dto import (
    GetReturnDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.query import (
    ListReturnDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_documents.dto import (
    ListReturnDocumentsResultDTO,
)


class ReturnDocumentQueryRepositoryProtocol(Protocol):
    """Определяет отдельный read-side изменений состояния."""

    async def get(
        self, query: GetReturnDocumentQuery
    ) -> GetReturnDocumentResultDTO | None:
        """Проецирует карточку и строки без восстановления Domain."""
        ...

    async def list(
        self, query: ListReturnDocumentsQuery
    ) -> ListReturnDocumentsResultDTO:
        """Читает страницу и total по одним фильтрам."""
        ...
