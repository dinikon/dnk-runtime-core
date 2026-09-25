from src.modules.contact_points.application.binding.command.sync_target_contact_points_command import (
    SyncTargetContactPointsCommand,
)
from src.modules.contact_points.domain.binding.service import ContactPointBindingService


class SyncTargetContactPointsUseCase:
    """Сохраняет массивы через domain service в UoW вызывающего модуля."""

    def __init__(self, service: ContactPointBindingService):
        self.service = service

    async def __call__(self, command: SyncTargetContactPointsCommand) -> None:
        """Синхронизирует переданные списки заблокированного target."""
        await self.service.sync(
            command.tenant_id,
            command.actor_id,
            command.target,
            command.phones,
            command.emails,
        )


__all__ = ["SyncTargetContactPointsUseCase"]
