from typing import Protocol

from src.modules.contact_point.application.dto import OwnerContactPointListDTO
from src.modules.contact_point.application.query.list_owner_contact_points_query import (
    ListOwnerContactPointsQuery,
)


class OwnerContactPointQueryRepositoryProtocol(Protocol):
    async def list_owner_contact_points(
        self,
        query: ListOwnerContactPointsQuery,
    ) -> OwnerContactPointListDTO: ...


__all__ = ["OwnerContactPointQueryRepositoryProtocol"]
