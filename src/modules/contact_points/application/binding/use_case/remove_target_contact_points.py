from src.modules.contact_points.application.binding.command.remove_target_contact_points_command import (
    RemoveTargetContactPointsCommand,
)
from src.modules.contact_points.domain.binding.repository import (
    ContactPointBindingRepositoryProtocol,
)


class RemoveTargetContactPointsUseCase:
    """Удаляет связи владельца, сохраняя точки в справочнике."""

    def __init__(self, repository: ContactPointBindingRepositoryProtocol):
        self.repository = repository

    async def __call__(self, command: RemoveTargetContactPointsCommand) -> None:
        """Удаляет только bindings текущего tenant и target."""
        await self.repository.remove_target(command.tenant_id, command.target)


__all__ = ["RemoveTargetContactPointsUseCase"]
