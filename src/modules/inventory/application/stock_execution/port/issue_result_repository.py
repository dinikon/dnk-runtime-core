from typing import Protocol
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.query import (
    GetIssueExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.dto import (
    GetIssueExecutionResultDTO,
)


class IssueExecutionResultRepositoryProtocol(Protocol):
    """Читает собственный неизменяемый результат выдачи без текущего состояния позиций."""

    async def get(
        self, query: GetIssueExecutionResultQuery
    ) -> GetIssueExecutionResultDTO | None:
        """Возвращает исторический результат исполнения в текущем tenant."""
        ...
