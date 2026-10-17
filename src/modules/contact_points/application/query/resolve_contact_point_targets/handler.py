from src.modules.contact_points.application.query.resolve_contact_point_targets.query import (
    ResolveContactPointTargetsQuery,
)
from src.modules.contact_points.domain.binding_repository import (
    ContactPointBindingRepositoryProtocol,
)
from src.modules.contact_points.domain.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.resolver import ContactPointResolver
from src.modules.contact_points.domain.contact_point_repository import (
    ContactPointRepositoryProtocol,
)


class ResolveContactPointTargetsHandler:
    """Ищет владельцев без создания отсутствующих точек."""

    def __init__(
        self,
        resolver: ContactPointResolver,
        points: ContactPointRepositoryProtocol,
        bindings: ContactPointBindingRepositoryProtocol,
    ):
        self.resolver, self.points, self.bindings = resolver, points, bindings

    async def execute(
        self, query: ResolveContactPointTargetsQuery
    ) -> tuple[ContactPointTargetVO, ...]:
        """Возвращает только target refs текущего tenant."""
        normalized = self.resolver.normalize(
            query.type, query.value, query.country_code
        )
        point = await self.points.find_by_canonical(
            query.tenant_id, query.type, normalized.value
        )
        return (
            ()
            if point is None
            else await self.bindings.list_targets(query.tenant_id, point.id)
        )


__all__ = ["ResolveContactPointTargetsHandler"]
