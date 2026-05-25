from typing import Protocol

from src.modules.contact_point.application.dto import (
    ContactPointBindingListDTO,
    ContactPointDTO,
    ContactPointListDTO,
    OwnerContactPointListDTO,
)
from src.modules.contact_point.application.query.get_contact_point_query import (
    GetContactPointQuery,
)
from src.modules.contact_point.application.query.list_contact_point_bindings_query import (
    ListContactPointBindingsQuery,
)
from src.modules.contact_point.application.query.list_contact_points_query import (
    ListContactPointsQuery,
)
from src.modules.contact_point.application.query.list_owner_contact_points_query import (
    ListOwnerContactPointsQuery,
)


class OwnerContactPointQueryRepositoryProtocol(Protocol):

    async def get_contact_point(
        self,
        query: GetContactPointQuery,
    ) -> ContactPointDTO | None: ...

    async def list_contact_points(
        self,
        query: ListContactPointsQuery,
    ) -> ContactPointListDTO: ...

    async def list_owner_contact_points(
        self,
        query: ListOwnerContactPointsQuery,
    ) -> OwnerContactPointListDTO: ...

    async def list_contact_point_bindings(
        self,
        query: ListContactPointBindingsQuery,
    ) -> ContactPointBindingListDTO: ...


__all__ = ["OwnerContactPointQueryRepositoryProtocol"]
