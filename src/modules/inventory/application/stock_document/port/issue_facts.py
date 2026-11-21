from typing import Protocol
from src.modules.inventory.application.stock_document.query.prepare_issue.query import (
    PrepareIssueQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_issue.dto import (
    PrepareIssueResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_issue_executions.query import (
    ListIssueExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_issue_executions.dto import (
    ListIssueExecutionsResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_issue_sources.query import (
    ListIssueSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_issue_sources.dto import (
    ListIssueSourcesResultDTO,
)


class IssueFactsQueryPort(Protocol):
    """Читает подготовку, физические источники и историю ISSUE без восстановления агрегатов."""

    async def prepare(self, query: PrepareIssueQuery) -> PrepareIssueResultDTO | None:
        """Возвращает согласованную версию и прогресс строк."""
        ...

    async def list_executions(
        self, query: ListIssueExecutionsQuery
    ) -> ListIssueExecutionsResultDTO | None:
        """Читает историю независимо от текущих количеств позиций."""
        ...

    async def sources(
        self, query: ListIssueSourcesQuery
    ) -> ListIssueSourcesResultDTO | None:
        """Ищет положительный запас; явный ID позволяет сверить и обнулённый источник."""
        ...
