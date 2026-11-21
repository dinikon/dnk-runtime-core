from src.modules.inventory.application.stock_document.port.write_off_facts import (
    WriteOffFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_write_off_executions.query import (
    ListWriteOffExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_write_off_executions.dto import (
    ListWriteOffExecutionsResultDTO,
)
from src.modules.inventory.domain.stock_document.write_off_error import (
    WriteOffFactNotFoundError,
)


class ListWriteOffExecutionsHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: WriteOffFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListWriteOffExecutionsQuery
    ) -> ListWriteOffExecutionsResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.list_executions(query)
        if result is None:
            raise WriteOffFactNotFoundError("Факт или документ не найден.")
        return result
