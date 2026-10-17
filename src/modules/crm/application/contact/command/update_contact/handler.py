from src.modules.crm.application.contact.command.update_contact.command import (
    UpdateContactCommand,
)
from src.modules.crm.application.contact.command.update_contact.dto import (
    UpdateContactResultDTO,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.shared.domain.time.clock_port import ClockPort


class UpdateContactHandler:
    """Изменяет агрегат под блокировкой в транзакции внешнего UoW."""

    def __init__(self, repository: ContactRepositoryProtocol, clock: ClockPort) -> None:
        self._repository = repository
        self._clock = clock

    async def execute(self, command: UpdateContactCommand) -> UpdateContactResultDTO:
        contact = await self._repository.get_for_update(command.contact_id)
        if contact is None:
            raise ContactNotFoundError("Contact not found.")
        current = contact.name
        changed = contact.update(
            first_name=(
                command.first_name
                if "first_name" in command.fields
                else current.first_name
            ),
            last_name=(
                command.last_name
                if "last_name" in command.fields
                else current.last_name
            ),
            middle_name=(
                command.middle_name
                if "middle_name" in command.fields
                else current.middle_name
            ),
            actor_id=command.actor_id,
            now=self._clock.now(),
        )
        if changed:
            await self._repository.save(contact)
        return UpdateContactResultDTO(
            id=contact.id.uuid,
            first_name=contact.name.first_name,
            last_name=contact.name.last_name,
            middle_name=contact.name.middle_name,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            created_by=contact.created_by.uuid,
            updated_by=contact.updated_by.uuid,
        )
