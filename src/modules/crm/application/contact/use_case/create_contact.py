from src.modules.crm.application.contact.command import CreateContactCommand
from src.modules.crm.application.contact.dto import ContactDTO, contact_dto
from src.modules.crm.domain.contact.entity import Contact
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class CreateContactUseCase:
    """Создаёт tenant-scoped CRM-контакт."""

    def __init__(self, repository: ContactRepositoryProtocol, clock: ClockPort):
        self.repository = repository
        self.clock = clock

    async def __call__(self, command: CreateContactCommand) -> ContactDTO:
        """Валидирует aggregate и сохраняет его через repository."""
        contact = Contact.create(
            contact_id=command.contact_id,
            actor_id=command.actor_id,
            now=self.clock.now(),
            first_name=command.first_name,
            last_name=command.last_name,
            middle_name=command.middle_name,
        )
        await self.repository.add(command.tenant_id, contact)
        return contact_dto(contact)


__all__ = ["CreateContactUseCase"]
