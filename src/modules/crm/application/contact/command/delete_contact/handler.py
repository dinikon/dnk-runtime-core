from src.modules.crm.application.contact.command.delete_contact.command import (
    DeleteContactCommand,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol


class DeleteContactHandler:
    """Удаляет найденный агрегат в транзакции внешнего UoW."""

    def __init__(self, repository: ContactRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, command: DeleteContactCommand) -> None:
        contact = await self._repository.get_for_update(command.contact_id)
        if contact is None:
            raise ContactNotFoundError("Contact not found.")
        await self._repository.delete(contact)
