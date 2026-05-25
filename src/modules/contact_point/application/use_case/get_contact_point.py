from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.application.dto import ContactPointDTO
from src.modules.contact_point.application.query import (
    GetContactPointQuery,
    OwnerContactPointQueryRepositoryProtocol,
)
from src.modules.contact_point.domain.contact_point import ContactPointNotFoundError


class GetContactPointUseCaseProtocol(Protocol):
    async def __call__(self, query: GetContactPointQuery) -> ContactPointDTO: ...


class GetContactPointUseCase:
    def __init__(
        self,
        *,
        query_repository: OwnerContactPointQueryRepositoryProtocol,
    ) -> None:
        self._query_repository = query_repository

    async def __call__(self, query: GetContactPointQuery) -> ContactPointDTO:
        contact_point = await self._query_repository.get_contact_point(query)
        if contact_point is None:
            raise ContactPointNotFoundError(str(query.contact_point_id))
        return contact_point


__all__ = [
    "GetContactPointUseCase",
    "GetContactPointUseCaseProtocol",
]
