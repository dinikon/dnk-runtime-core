from src.modules.inventory.application.stock_document.port.status_change_facts import (
    StatusChangeFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_status_change_executions.query import (
    ListStatusChangeExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_status_change_executions.dto import (
    ListStatusChangeExecutionsResultDTO,
)
from src.modules.inventory.domain.stock_document.status_change_error import (
    StatusChangeFactNotFoundError,
)


class ListStatusChangeExecutionsHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: StatusChangeFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListStatusChangeExecutionsQuery
    ) -> ListStatusChangeExecutionsResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.list_executions(query)
        if result is None:
            raise StatusChangeFactNotFoundError("Факт или документ не найден.")
        return result
