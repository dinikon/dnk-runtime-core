from src.modules.inventory.application.stock_document.internal_move_read_service import (
    InternalMoveDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.query import (
    ListInternalMoveDocumentsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_documents.dto import (
    ListInternalMoveDocumentsResultDTO,
)


class ListInternalMoveDocumentsHandler:
    """Выполняет отдельный сценарий чтения перемещений."""

    def __init__(self, reader: InternalMoveDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: ListInternalMoveDocumentsQuery
    ) -> ListInternalMoveDocumentsResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.list(query)
