from src.modules.inventory.application.stock_execution.port.issue_result_repository import (
    IssueExecutionResultRepositoryProtocol,
)
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.query import (
    GetIssueExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_issue_execution_result.dto import (
    GetIssueExecutionResultDTO,
)
from src.modules.inventory.domain.stock_document.issue_error import (
    IssueFactNotFoundError,
)


class GetIssueExecutionResultHandler:
    """Возвращает исторические источники, дельты и исходные количества до/после."""

    def __init__(self, repository: IssueExecutionResultRepositoryProtocol) -> None:
        """Получает независимый read-порт собственного результата."""
        self._repository = repository

    async def execute(
        self, query: GetIssueExecutionResultQuery
    ) -> GetIssueExecutionResultDTO:
        """Отличает отсутствующий факт от сохранённого первоначального ответа."""
        result = await self._repository.get(query)
        if result is None:
            raise IssueFactNotFoundError("Результат расхода не найден.")
        return result
