from typing import Protocol
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.query import (
    GetStatusChangeExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_status_change_execution_result.dto import (
    GetStatusChangeExecutionResultDTO,
)


class StatusChangeExecutionResultRepositoryProtocol(Protocol):
    """Читает собственный неизменяемый результат изменения состояния без текущего состояния позиций."""

    async def get(
        self, query: GetStatusChangeExecutionResultQuery
    ) -> GetStatusChangeExecutionResultDTO | None:
        """Возвращает исторический результат исполнения в текущем tenant."""
        ...
