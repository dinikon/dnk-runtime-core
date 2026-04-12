from typing import Protocol

from src.modules.crm.application.contact.command.rename_contact_command import (
    RenameContactCommand,
)
from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.service import ContactService


class UpdateContactUseCaseProtocol(Protocol):
    """Порт use case обновления контакта."""

    async def __call__(self, command: RenameContactCommand) -> ContactDTO:
        """Обновляет контакт и возвращает DTO."""
        ...


class UpdateContactUseCase:
    """Use case обновления CRM-контакта через доменный сервис."""

    def __init__(self, service: ContactService) -> None:
        """Инициализирует use case доменным сервисом контактов."""
        self._service = service

    async def __call__(self, command: RenameContactCommand) -> ContactDTO:
        """Выполняет команду обновления контакта и мапит entity в DTO."""
        contact = await self._service.rename_contact(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
            last_name=command.last_name,
            first_name=command.first_name,
            middle_name=command.middle_name,
            status=command.status,
            tags=command.tags,
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
