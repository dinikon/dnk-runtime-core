from typing import Protocol
from src.modules.price_lists.application.sync_run.dto.sync_run_dto import SyncRunDTO
from src.modules.price_lists.application.sync_run.query.list_runs_query import (
    ListRunsQuery,
)


class SyncRunQueryRepository(Protocol):
    """Порт публичной истории синхронизации."""

    async def list_runs(self, query: ListRunsQuery) -> list[SyncRunDTO]: ...


__all__ = ["SyncRunQueryRepository"]
