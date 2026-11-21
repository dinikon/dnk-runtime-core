from typing import Protocol
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.query import (
    GetReturnExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.dto import (
    GetReturnExecutionResultDTO,
)


class ReturnExecutionResultRepositoryProtocol(Protocol):
    """Читает собственный неизменяемый результат возврата без текущего состояния позиций."""

    async def get(
        self, query: GetReturnExecutionResultQuery
    ) -> GetReturnExecutionResultDTO | None:
        """Возвращает исторический результат исполнения в текущем tenant."""
        ...
