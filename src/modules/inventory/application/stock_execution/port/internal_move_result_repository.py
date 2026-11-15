from typing import Protocol
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.query import (
    GetInternalMoveExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_internal_move_execution_result.dto import (
    GetInternalMoveExecutionResultDTO,
)


class InternalMoveExecutionResultRepositoryProtocol(Protocol):
    """Читает собственный неизменяемый результат перемещения без текущего состояния позиций."""

    async def get(
        self, query: GetInternalMoveExecutionResultQuery
    ) -> GetInternalMoveExecutionResultDTO | None:
        """Возвращает исторический результат исполнения в текущем tenant."""
        ...
