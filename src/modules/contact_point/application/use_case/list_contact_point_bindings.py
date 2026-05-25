from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.application.dto import ContactPointBindingListDTO
from src.modules.contact_point.application.query import (
    ListContactPointBindingsQuery,
    OwnerContactPointQueryRepositoryProtocol,
)


class ListContactPointBindingsUseCaseProtocol(Protocol):
    async def __call__(
        self,
        query: ListContactPointBindingsQuery,
    ) -> ContactPointBindingListDTO: ...


class ListContactPointBindingsUseCase:
    def __init__(
        self,
        *,
        query_repository: OwnerContactPointQueryRepositoryProtocol,
    ) -> None:
        self._query_repository = query_repository

    async def __call__(
        self,
        query: ListContactPointBindingsQuery,
    ) -> ContactPointBindingListDTO:
        return await self._query_repository.list_contact_point_bindings(query)


__all__ = [
    "ListContactPointBindingsUseCase",
    "ListContactPointBindingsUseCaseProtocol",
]
