from src.modules.inventory.application.stock_document.port.receipt_posting import (
    ReceiptFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.query import (
    ListReceiptExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.dto import (
    ListReceiptExecutionsResultDTO,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)


class ListReceiptExecutionsHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: ReceiptFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListReceiptExecutionsQuery
    ) -> ListReceiptExecutionsResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.list_executions(query)
        if result is None:
            raise ReceiptFactNotFoundError("Факт или документ не найден.")
        return result
