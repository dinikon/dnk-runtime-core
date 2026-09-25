from src.modules.contact_points.application.binding.query.get_targets_contact_points_query import (
    GetTargetsContactPointsQuery,
)
from src.modules.contact_points.application.binding.dto.binding_dto import (
    ContactPointBindingDTO,
    binding_dto,
)
from src.modules.contact_points.domain.binding.repository import (
    ContactPointBindingRepositoryProtocol,
)


class GetTargetsContactPointsUseCase:
    """Читает контактные массивы одним пакетным запросом."""

    def __init__(self, repository: ContactPointBindingRepositoryProtocol):
        self.repository = repository

    async def __call__(
        self, query: GetTargetsContactPointsQuery
    ) -> tuple[ContactPointBindingDTO, ...]:
        """Возвращает DTO в порядке target, type, position, id."""
        return tuple(
            binding_dto(row)
            for row in await self.repository.list_for_targets(
                query.tenant_id, query.targets
            )
        )


__all__ = ["GetTargetsContactPointsUseCase"]
