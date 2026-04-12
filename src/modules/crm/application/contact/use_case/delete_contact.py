from typing import Protocol

from src.modules.crm.application.contact.command.delete_contact_command import (
    DeleteContactCommand,
)
from src.modules.crm.domain.contact.service import ContactService


class DeleteContactUseCaseProtocol(Protocol):
    """Порт use case удаления контакта."""

    async def __call__(self, command: DeleteContactCommand) -> None:
        """Удаляет контакт tenant."""
        ...


class DeleteContactUseCase:
    """Use case удаления CRM-контакта через доменный сервис."""

    def __init__(self, service: ContactService):
        """Инициализирует use case доменным сервисом контактов."""
        self._service = service

    async def __call__(self, command: DeleteContactCommand) -> None:
        """Выполняет команду удаления контакта."""
        await self._service.delete_contact(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
        )
