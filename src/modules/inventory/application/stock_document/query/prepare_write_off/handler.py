from src.modules.inventory.application.stock_document.port.write_off_facts import (
    WriteOffFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.prepare_write_off.query import (
    PrepareWriteOffQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_write_off.dto import (
    PrepareWriteOffResultDTO,
)
from src.modules.inventory.domain.stock_document.error import StockDocumentNotFoundError


class PrepareWriteOffHandler:
    """Читает подготовку формы через специализированную проекцию."""

    def __init__(self, repository: WriteOffFactsQueryPort) -> None:
        """Принимает read-порт общей tenant-сессии."""
        self._repository = repository

    async def execute(self, query: PrepareWriteOffQuery) -> PrepareWriteOffResultDTO:
        """Возвращает текущую версию и остатки плана либо сообщает об отсутствии документа."""
        result = await self._repository.prepare(query)
        if result is None:
            raise StockDocumentNotFoundError("Списание не найдено.")
        return result
