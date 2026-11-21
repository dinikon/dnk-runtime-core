from src.modules.inventory.application.stock_document.port.receipt_posting import (
    ReceiptFactsQueryPort,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution.query import (
    GetStockExecutionQuery,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution.dto import (
    GetStockExecutionResultDTO,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)


class GetStockExecutionHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: ReceiptFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: GetStockExecutionQuery
    ) -> GetStockExecutionResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.get_execution(query.identifier)
        if result is None:
            raise ReceiptFactNotFoundError("Факт или документ не найден.")
        return result
