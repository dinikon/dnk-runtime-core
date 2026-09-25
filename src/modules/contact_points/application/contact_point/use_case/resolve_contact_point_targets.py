from src.modules.contact_points.application.contact_point.query.resolve_contact_point_targets_query import (
    ResolveContactPointTargetsQuery,
)
from src.modules.contact_points.domain.binding.repository import (
    ContactPointBindingRepositoryProtocol,
)
from src.modules.contact_points.domain.binding.value_object.target import (
    ContactPointTargetVO,
)
from src.modules.contact_points.domain.contact_point.service import ContactPointResolver
from src.modules.contact_points.domain.contact_point.repository import (
    ContactPointRepositoryProtocol,
)


class ResolveContactPointTargetsUseCase:
    """Ищет владельцев без создания отсутствующих точек."""

    def __init__(
        self,
        resolver: ContactPointResolver,
        points: ContactPointRepositoryProtocol,
        bindings: ContactPointBindingRepositoryProtocol,
    ):
        self.resolver, self.points, self.bindings = resolver, points, bindings

    async def __call__(
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


__all__ = ["ResolveContactPointTargetsUseCase"]
