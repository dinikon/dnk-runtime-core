from src.modules.inventory.application.stock_document.internal_move_read_service import (
    InternalMoveDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.query import (
    GetInternalMoveDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_internal_move_document.dto import (
    GetInternalMoveDocumentResultDTO,
)


class GetInternalMoveDocumentHandler:
    """Выполняет отдельный сценарий чтения перемещений."""

    def __init__(self, reader: InternalMoveDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: GetInternalMoveDocumentQuery
    ) -> GetInternalMoveDocumentResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.get(query)
