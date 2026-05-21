from __future__ import annotations

from typing import Protocol

from src.modules.contact_point.application.dto import OwnerContactPointListDTO
from src.modules.contact_point.application.ports import (
    ContactPointObjectFeatureGatePort,
    OwnerResolverPort,
)
from src.modules.contact_point.application.query import (
    ListOwnerContactPointsQuery,
    OwnerContactPointQueryRepositoryProtocol,
)
from src.modules.contact_point.domain.binding import (
    ContactPointOwnerNotFoundError,
    OwnerContactPointBinding,
)


class ListOwnerContactPointsUseCaseProtocol(Protocol):
    async def __call__(
        self,
        query: ListOwnerContactPointsQuery,
    ) -> OwnerContactPointListDTO: ...


class ListOwnerContactPointsUseCase:
    def __init__(
        self,
        *,
        owner_resolver: OwnerResolverPort,
        feature_gate: ContactPointObjectFeatureGatePort,
        query_repository: OwnerContactPointQueryRepositoryProtocol,
    ) -> None:
        self._owner_resolver = owner_resolver
        self._feature_gate = feature_gate
        self._query_repository = query_repository

    async def __call__(
        self,
        query: ListOwnerContactPointsQuery,
    ) -> OwnerContactPointListDTO:
        owner = OwnerContactPointBinding(
            owner_object_id=query.owner_object_id,
            owner_record_id=query.owner_record_id,
        )
        owner_exists = await self._owner_resolver.exists(
            tenant_id=query.tenant_id,
            owner=owner,
        )
        if not owner_exists:
            raise ContactPointOwnerNotFoundError(
                str(query.owner_object_id),
                str(query.owner_record_id),
            )

        await self._feature_gate.assert_contact_point_enabled(
            tenant_id=query.tenant_id,
            owner_object_id=query.owner_object_id,
        )
        return await self._query_repository.list_owner_contact_points(query)


__all__ = [
    "ListOwnerContactPointsUseCase",
    "ListOwnerContactPointsUseCaseProtocol",
]
