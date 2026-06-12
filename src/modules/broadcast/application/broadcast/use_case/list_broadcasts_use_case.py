from typing import Protocol

from src.modules.broadcast.application.broadcast.dto import BroadcastListDTO
from src.modules.broadcast.application.broadcast.query import ListBroadcastsQuery
from src.modules.broadcast.application.broadcast.repository import (
    BroadcastQueryRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class ListBroadcastsUseCaseProtocol(Protocol):
    """Порт use case списка broadcast definitions."""

    async def __call__(self, query: ListBroadcastsQuery) -> BroadcastListDTO:
        """Возвращает страницу broadcast definitions."""
        ...


class ListBroadcastsUseCase:
    """Use case списка broadcast definitions tenant."""

    def __init__(
        self,
        *,
        query_repository: BroadcastQueryRepositoryProtocol,
    ) -> None:
        """Инициализирует use case query repository."""
        self._query_repository = query_repository

    async def __call__(self, query: ListBroadcastsQuery) -> BroadcastListDTO:
        """Возвращает страницу broadcast definitions по runtime DSL."""
        return await self._query_repository.list(
            tenant_id=EntityIdVO.from_value(query.tenant_id),
            filter_dsl=query.filter_dsl,
            sort_dsl=query.sort_dsl,
            limit=query.limit,
            offset=query.offset,
        )
