from src.modules.inventory.application.stock_document.port.status_change_facts import (
    StatusChangeFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.prepare_status_change.query import (
    PrepareStatusChangeQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_status_change.dto import (
    PrepareStatusChangeResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class PrepareStatusChangeHandler:
    """Читает подготовку формы через специализированную проекцию."""

    def __init__(self, repository: StatusChangeFactsQueryPort) -> None:
        """Принимает read-порт общей tenant-сессии."""
        self._repository = repository

    async def execute(
        self, query: PrepareStatusChangeQuery
    ) -> PrepareStatusChangeResultDTO:
        """Возвращает текущую версию и остатки плана либо сообщает об отсутствии документа."""
        result = await self._repository.prepare(query)
        if result is None:
            raise StockDocumentNotFoundError("Изменение состояния не найдено.")
        return result
