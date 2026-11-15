from typing import Protocol
from src.modules.inventory.application.stock_document.query.get_status_change_document.query import (
    GetStatusChangeDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.dto import (
    GetStatusChangeDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.query import (
    ListStatusChangeDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_status_change_documents.dto import (
    ListStatusChangeDocumentsResultDTO,
)


class StatusChangeDocumentQueryRepositoryProtocol(Protocol):
    """Определяет отдельный read-side изменений состояния."""

    async def get(
        self, query: GetStatusChangeDocumentQuery
    ) -> GetStatusChangeDocumentResultDTO | None:
        """Проецирует карточку и строки без восстановления Domain."""
        ...

    async def list(
        self, query: ListStatusChangeDocumentsQuery
    ) -> ListStatusChangeDocumentsResultDTO:
        """Читает страницу и total по одним фильтрам."""
        ...
