from src.modules.crm.application.contact_points.port import ContactPointsPort
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.command import DeleteContactCommand
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol


class DeleteContactUseCase:
    """Физически удаляет tenant-scoped контакт."""

    def __init__(
        self, repository: ContactRepositoryProtocol, contact_points: ContactPointsPort
    ):
        self.repository = repository
        self.contact_points = contact_points

    async def __call__(self, command: DeleteContactCommand) -> None:
        """Удаляет запись либо поднимает ContactNotFoundError."""
        await self.repository.get(
            command.tenant_id, command.contact_id, for_update=True
        )
        await self.contact_points.remove(
            command.tenant_id,
            "crm.contact",
            EntityIdVO.from_value(command.contact_id.uuid),
        )
        await self.repository.delete(command.tenant_id, command.contact_id)


__all__ = ["DeleteContactUseCase"]
