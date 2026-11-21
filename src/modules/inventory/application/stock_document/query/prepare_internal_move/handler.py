from src.modules.inventory.application.stock_document.port.internal_move_facts import (
    InternalMoveFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.prepare_internal_move.query import (
    PrepareInternalMoveQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_internal_move.dto import (
    PrepareInternalMoveResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class PrepareInternalMoveHandler:
    """Читает подготовку формы через специализированную проекцию."""

    def __init__(self, repository: InternalMoveFactsQueryPort) -> None:
        """Принимает read-порт общей tenant-сессии."""
        self._repository = repository

    async def execute(
        self, query: PrepareInternalMoveQuery
    ) -> PrepareInternalMoveResultDTO:
        """Возвращает текущую версию и остатки плана либо сообщает об отсутствии документа."""
        result = await self._repository.prepare(query)
        if result is None:
            raise StockDocumentNotFoundError("Перемещение не найдено.")
        return result
