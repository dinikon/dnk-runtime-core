from src.modules.inventory.application.stock_document.port.return_facts import (
    ReturnFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.query import (
    ListReturnExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.dto import (
    ListReturnExecutionsResultDTO,
)
from src.modules.inventory.domain.stock_document.return_error import (
    ReturnFactNotFoundError,
)


class ListReturnExecutionsHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: ReturnFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListReturnExecutionsQuery
    ) -> ListReturnExecutionsResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.list_executions(query)
        if result is None:
            raise ReturnFactNotFoundError("Факт или документ не найден.")
        return result
