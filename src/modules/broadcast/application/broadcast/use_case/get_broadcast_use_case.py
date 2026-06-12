from typing import Protocol

from src.modules.broadcast.application.broadcast.dto import BroadcastDTO
from src.modules.broadcast.application.broadcast.query import GetBroadcastQuery
from src.modules.broadcast.application.broadcast.repository import (
    BroadcastQueryRepositoryProtocol,
)
from src.modules.broadcast.domain.broadcast.value_object.broadcast_id import (
    BroadcastIdVO,
)
from src.modules.shared import EntityIdVO


class GetBroadcastUseCaseProtocol(Protocol):
    """Порт use case чтения одной broadcast definition."""

    async def __call__(self, query: GetBroadcastQuery) -> BroadcastDTO | None:
        """Возвращает одну broadcast definition."""
        ...


class GetBroadcastUseCase:
    """Use case чтения одной broadcast definition tenant."""

    def __init__(
        self,
        *,
        query_repository: BroadcastQueryRepositoryProtocol,
    ) -> None:
        """Инициализирует use case query repository."""
        self._query_repository = query_repository

    async def __call__(self, query: GetBroadcastQuery) -> BroadcastDTO | None:
        """Возвращает broadcast definition по id."""
        return await self._query_repository.get(
            tenant_id=EntityIdVO.from_value(query.tenant_id),
            broadcast_id=BroadcastIdVO.from_value(query.broadcast_id),
        )


__all__ = ["GetBroadcastUseCase", "GetBroadcastUseCaseProtocol"]
