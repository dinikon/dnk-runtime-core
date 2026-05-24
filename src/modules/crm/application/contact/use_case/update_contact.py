from typing import Protocol

from src.modules.crm.application.contact.command.rename_contact_command import (
    RenameContactCommand,
)
from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.error import ContactNotFoundError
from src.modules.crm.domain.contact.repository import ContactCommandRepositoryProtocol
from src.modules.shared.domain.time import ClockPort


class UpdateContactUseCaseProtocol(Protocol):
    """Порт use case обновления контакта."""

    async def __call__(self, command: RenameContactCommand) -> ContactDTO:
        """Обновляет контакт и возвращает DTO."""
        ...


class UpdateContactUseCase:
    """Use case обновления CRM-контакта."""

    def __init__(
        self,
        *,
        command_repository: ContactCommandRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case командным репозиторием и clock-портом."""
        self._command_repository = command_repository
        self._clock = clock

    async def __call__(self, command: RenameContactCommand) -> ContactDTO:
        """Выполняет команду обновления контакта и мапит entity в DTO."""
        contact = await self._command_repository.load(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
        )
        if contact is None:
            raise ContactNotFoundError(str(command.contact_id))

        contact.rename(
            now=self._clock.now(),
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
