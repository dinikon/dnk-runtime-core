from src.modules.inventory.application.stock_document.port.issue_facts import (
    IssueFactsQueryPort,
)
from src.modules.inventory.application.stock_document.query.list_issue_executions.query import (
    ListIssueExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_issue_executions.dto import (
    ListIssueExecutionsResultDTO,
)
from src.modules.inventory.domain.stock_document.issue_error import (
    IssueFactNotFoundError,
)


class ListIssueExecutionsHandler:
    """Читает собственную проекцию истории без команд и восстановления агрегатов."""

    def __init__(self, repository: IssueFactsQueryPort) -> None:
        """Получает порт чтения текущего tenant."""
        self._repository = repository

    async def execute(
        self, query: ListIssueExecutionsQuery
    ) -> ListIssueExecutionsResultDTO:
        """Возвращает конкретный результат либо сообщает об отсутствии факта."""
        result = await self._repository.list_executions(query)
        if result is None:
            raise IssueFactNotFoundError("Факт или документ не найден.")
        return result
