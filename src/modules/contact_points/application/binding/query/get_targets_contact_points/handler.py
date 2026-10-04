from src.modules.contact_points.application.binding.query.get_targets_contact_points.query import (
    GetTargetsContactPointsQuery,
)
from src.modules.contact_points.application.binding.query.get_targets_contact_points.dto import (
    ContactPointBindingDTO,
    binding_dto,
)
from src.modules.contact_points.domain.binding.repository import (
    ContactPointBindingRepositoryProtocol,
)


class GetTargetsContactPointsHandler:
    """Читает контактные массивы одним пакетным запросом."""

    def __init__(self, repository: ContactPointBindingRepositoryProtocol):
        self.repository = repository

    async def execute(
        self, query: GetTargetsContactPointsQuery
    ) -> tuple[ContactPointBindingDTO, ...]:
        """Возвращает DTO в порядке target, type, position, id."""
        return tuple(
            binding_dto(row)
            for row in await self.repository.list_for_targets(
                query.tenant_id, query.targets
            )
        )


__all__ = ["GetTargetsContactPointsHandler"]
