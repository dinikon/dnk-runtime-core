from src.modules.inventory.application.stock_document.port.receipt_posting import (
    ReceiptFactsQueryPort,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting.query import (
    GetStockPostingQuery,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting.dto import (
    GetStockPostingResultDTO,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)


class GetStockPostingHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: ReceiptFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(self, query: GetStockPostingQuery) -> GetStockPostingResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.get_posting(query.identifier)
        if result is None:
            raise ReceiptFactNotFoundError("Факт или документ не найден.")
        return result
