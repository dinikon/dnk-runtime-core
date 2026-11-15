from src.modules.inventory.application.stock_document.write_off_read_service import (
    WriteOffDocumentReadService,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.query import (
    GetWriteOffDocumentQuery,
)
from src.modules.inventory.application.stock_document.query.get_write_off_document.dto import (
    GetWriteOffDocumentResultDTO,
)


class GetWriteOffDocumentHandler:
    """Выполняет отдельный сценарий чтения списаний."""

    def __init__(self, reader: WriteOffDocumentReadService) -> None:
        """Принимает сервис публичных проекций."""
        self._reader = reader

    async def execute(
        self, query: GetWriteOffDocumentQuery
    ) -> GetWriteOffDocumentResultDTO:
        """Возвращает DTO собственного сценария."""
        return await self._reader.get(query)
