from src.modules.crm.application.contact.command.create_contact.command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.command.create_contact.dto import (
    CreateContactResultDTO,
)
from src.modules.crm.domain.contact.aggregate import Contact
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class CreateContactHandler:
    """Создаёт и сохраняет контакт внутри внешнего UoW."""

    def __init__(self, repository: ContactRepositoryProtocol, clock: ClockPort) -> None:
        """Получает абстрактные порты хранения и времени."""
        self._repository = repository
        self._clock = clock

    async def execute(self, command: CreateContactCommand) -> CreateContactResultDTO:
        """Делегирует проверку имени домену и возвращает данные нового контакта."""
        contact = Contact.create(
            contact_id=command.contact_id,
            first_name=command.first_name,
            last_name=command.last_name,
            middle_name=command.middle_name,
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        await self._repository.add(command.tenant_id, contact)
        return CreateContactResultDTO(
            id=contact.id.uuid,
            first_name=contact.name.first_name,
            last_name=contact.name.last_name,
            middle_name=contact.name.middle_name,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            created_by=contact.created_by.uuid,
            updated_by=contact.updated_by.uuid,
        )
