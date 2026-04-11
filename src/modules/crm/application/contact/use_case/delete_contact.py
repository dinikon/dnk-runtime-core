from typing import Protocol

from modules.crm.application.contact.command.delete_contact_command import (
    DeleteContactCommand,
)
from modules.crm.domain.contact.service import ContactService


class DeleteContactUseCaseProtocol(Protocol):
    async def __call__(self, command: DeleteContactCommand) -> None: ...


class DeleteContactUseCase:
    def __init__(self, service: ContactService):
        self._service = service

    async def __call__(self, command: DeleteContactCommand) -> None:
        await self._service.delete_contact(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
        )
