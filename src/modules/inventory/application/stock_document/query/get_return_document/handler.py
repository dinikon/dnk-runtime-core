from src.modules.inventory.application.stock_document.return_read_service import (
    ReturnDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_return_document.query import (
    GetReturnDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_return_document.dto import (
    GetReturnDocumentResultDTO,
)


class GetReturnDocumentHandler:
    """Выполняет отдельный сценарий чтения изменений состояния."""

    def __init__(self, reader: ReturnDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: GetReturnDocumentQuery
    ) -> GetReturnDocumentResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.get(query)
