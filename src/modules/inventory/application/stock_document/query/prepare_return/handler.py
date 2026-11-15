from src.modules.inventory.application.stock_document.port.return_facts import (
    ReturnFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.prepare_return.query import (
    PrepareReturnQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_return.dto import (
    PrepareReturnResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class PrepareReturnHandler:
    """Читает подготовку формы через специализированную проекцию."""

    def __init__(self, repository: ReturnFactsQueryPort) -> None:
        """Принимает read-порт общей tenant-сессии."""
        self._repository = repository

    async def execute(self, query: PrepareReturnQuery) -> PrepareReturnResultDTO:
        """Возвращает текущую версию и остатки плана либо сообщает об отсутствии документа."""
        result = await self._repository.prepare(query)
        if result is None:
            raise StockDocumentNotFoundError("Возврат не найдено.")
        return result
