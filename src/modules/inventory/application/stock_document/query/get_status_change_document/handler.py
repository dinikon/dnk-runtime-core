from src.modules.inventory.application.stock_document.status_change_read_service import (
    StatusChangeDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.query import (
    GetStatusChangeDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_status_change_document.dto import (
    GetStatusChangeDocumentResultDTO,
)


class GetStatusChangeDocumentHandler:
    """Выполняет отдельный сценарий чтения изменений состояния."""

    def __init__(self, reader: StatusChangeDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: GetStatusChangeDocumentQuery
    ) -> GetStatusChangeDocumentResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.get(query)
