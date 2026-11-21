from typing import Protocol
from src.modules.inventory.application.stock_document.query.get_internal_move_document.query import (
    GetInternalMoveDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.dto import (
    GetInternalMoveDocumentResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.query import (
    ListInternalMoveDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.dto import (
    ListInternalMoveDocumentsResultDTO,
)


class InternalMoveDocumentQueryRepositoryProtocol(Protocol):
    """Определяет отдельный read-side перемещений."""

    async def get(
        self, query: GetInternalMoveDocumentQuery
    ) -> GetInternalMoveDocumentResultDTO | None:
        """Проецирует карточку и строки без восстановления Domain."""
        ...

    async def list(
        self, query: ListInternalMoveDocumentsQuery
    ) -> ListInternalMoveDocumentsResultDTO:
        """Читает страницу и total по одним фильтрам."""
        ...
