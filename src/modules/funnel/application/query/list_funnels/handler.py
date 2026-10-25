from dataclasses import asdict
from src.modules.funnel.application.query.list_funnels.query import ListFunnelsQuery
from src.modules.funnel.application.query.list_funnels.dto import ListFunnelsResultDTO
from src.modules.funnel.application.port.query_repository import (
    FunnelQueryRepositoryProtocol,
)
from src.modules.funnel.domain.error import FunnelNotFoundError, FunnelError


class ListFunnelsHandler:
    """Читает конкретную проекцию без восстановления Domain."""

    def __init__(self, repository: FunnelQueryRepositoryProtocol) -> None:
        """Принимает порт чтения."""
        self._repository = repository

    async def execute(self, query: ListFunnelsQuery) -> ListFunnelsResultDTO:
        """Возвращает типизированный результат чтения."""
        if (
            query.offset < 0
            or not 1 <= query.limit <= 100
            or query.model_key not in (None, "crm.lead", "crm.deal")
        ):
            raise FunnelError("Некорректные фильтры.")
        rows, total = await self._repository.list(
            query.model_key, query.search, query.offset, query.limit
        )
        return ListFunnelsResultDTO(rows, total, query.offset, query.limit)
