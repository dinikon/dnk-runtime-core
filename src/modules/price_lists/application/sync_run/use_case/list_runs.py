from src.modules.price_lists.application.sync_run.query.list_runs_query import (
    ListRunsQuery,
)
from src.modules.price_lists.application.sync_run.query.repository import (
    SyncRunQueryRepository,
)


class ListRunsUseCase:
    """Выполняет типизированный запрос list_runs."""

    def __init__(self, repository: SyncRunQueryRepository):
        self.repository = repository

    async def __call__(self, query: ListRunsQuery):
        """Выполняет сценарий через внедрённые доменные порты."""
        return await self.repository.list_runs(query)


__all__ = ["ListRunsUseCase"]
