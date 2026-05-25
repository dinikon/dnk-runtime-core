from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.application.dto import ContactPointListDTO
from src.modules.contact_point.application.query import (
    ListContactPointsQuery,
    OwnerContactPointQueryRepositoryProtocol,
)


class ListContactPointsUseCaseProtocol(Protocol):
    async def __call__(self, query: ListContactPointsQuery) -> ContactPointListDTO: ...


class ListContactPointsUseCase:
    def __init__(
        self,
        *,
        query_repository: OwnerContactPointQueryRepositoryProtocol,
    ) -> None:
        self._query_repository = query_repository

    async def __call__(self, query: ListContactPointsQuery) -> ContactPointListDTO:
        return await self._query_repository.list_contact_points(query)


__all__ = [
    "ListContactPointsUseCase",
    "ListContactPointsUseCaseProtocol",
]
