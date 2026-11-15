from typing import Protocol
from src.modules.inventory.application.stock_execution.query.get_write_off_execution_result.query import (
    GetWriteOffExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_write_off_execution_result.dto import (
    GetWriteOffExecutionResultDTO,
)


class WriteOffExecutionResultRepositoryProtocol(Protocol):
    """Читает собственный неизменяемый результат списания без текущего состояния позиций."""

    async def get(
        self, query: GetWriteOffExecutionResultQuery
    ) -> GetWriteOffExecutionResultDTO | None:
        """Возвращает исторический результат исполнения в текущем tenant."""
        ...
