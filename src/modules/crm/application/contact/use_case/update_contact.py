from src.modules.crm.application.contact.command import UpdateContactCommand
from src.modules.crm.application.contact.dto import ContactDTO, contact_dto
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class UpdateContactUseCase:
    """Обновляет ФИО tenant-scoped контакта."""

    def __init__(self, repository: ContactRepositoryProtocol, clock: ClockPort):
        self.repository = repository
        self.clock = clock

    async def __call__(self, command: UpdateContactCommand) -> ContactDTO:
        """Блокирует aggregate и сохраняет только реальное изменение."""
        contact = await self.repository.get(
            command.tenant_id, command.contact_id, for_update=True
        )
        changed = contact.update(
            actor_id=command.actor_id,
            now=self.clock.now(),
            first_name=command.first_name,
            last_name=command.last_name,
            middle_name=command.middle_name,
        )
        if changed:
            await self.repository.save(command.tenant_id, contact)
        return contact_dto(contact)


__all__ = ["UpdateContactUseCase"]
