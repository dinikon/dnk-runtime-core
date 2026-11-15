from src.modules.inventory.application.stock_document.port.internal_move_facts import (
    InternalMoveFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.query import (
    ListInternalMoveExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.dto import (
    ListInternalMoveExecutionsResultDTO,
)
from src.modules.inventory.domain.stock_document.internal_move_error import (
    InternalMoveFactNotFoundError,
)


class ListInternalMoveExecutionsHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: InternalMoveFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListInternalMoveExecutionsQuery
    ) -> ListInternalMoveExecutionsResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.list_executions(query)
        if result is None:
            raise InternalMoveFactNotFoundError("Факт или документ не найден.")
        return result
