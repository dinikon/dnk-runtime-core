from typing import Protocol

from src.modules.crm.application.contact.command.create_contact_command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.repository import ContactCommandRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class CreateContactUseCaseProtocol(Protocol):
    """Порт use case создания контакта."""

    async def __call__(self, command: CreateContactCommand) -> ContactDTO:
        """Создает контакт и возвращает DTO."""
        ...


class CreateContactUseCase:
    """Use case создания CRM-контакта."""

    def __init__(
        self,
        *,
        command_repository: ContactCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case командным репозиторием и clock-портом."""
        self._command_repository = command_repository
        self._clock = clock

    async def __call__(self, command: CreateContactCommand) -> ContactDTO:
        """Выполняет команду создания контакта и мапит entity в DTO."""
        now = self._clock.now()
        contact = ContactEntity.create(
            id_=command.contact_id,
            now=now,
            first_name=command.first_name,
            last_name=command.last_name,
            middle_name=command.middle_name,
            status=command.status,
            tags=command.tags,
        )
        contact = await self._command_repository.save(
            tenant_id=command.tenant_id,
            contact=contact,
        )
        return self._to_dto(contact)

    @staticmethod
    def _to_dto(contact: ContactEntity) -> ContactDTO:
        """Мапит ContactEntity в ContactDTO."""
        return ContactDTO(
            id=contact.id.uuid,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            last_name=contact.contact_name.last_name,
            first_name=contact.contact_name.first_name,
            middle_name=contact.contact_name.middle_name,
            status=contact.status,
            tags=list(contact.tags),
        )
