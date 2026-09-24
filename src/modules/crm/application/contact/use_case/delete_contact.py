from src.modules.crm.application.contact.command import DeleteContactCommand
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol


class DeleteContactUseCase:
    """Физически удаляет tenant-scoped контакт."""

    def __init__(self, repository: ContactRepositoryProtocol):
        self.repository = repository

    async def __call__(self, command: DeleteContactCommand) -> None:
        """Удаляет запись либо поднимает ContactNotFoundError."""
        await self.repository.delete(command.tenant_id, command.contact_id)


__all__ = ["DeleteContactUseCase"]
