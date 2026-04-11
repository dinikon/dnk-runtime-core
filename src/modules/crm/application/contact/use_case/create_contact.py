from typing import Protocol

from src.modules.crm.application.contact.command.create_contact_command import (
    CreateContactCommand,
)
from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.domain.contact.service import ContactService


class CreateContactUseCaseProtocol(Protocol):
    async def __call__(self, command: CreateContactCommand) -> ContactDTO: ...


class CreateContactUseCase:
    def __init__(self, service: ContactService):
        self._service = service

    async def __call__(self, command: CreateContactCommand) -> ContactDTO:

        contact = await self._service.create_contact(
            tenant_id=command.tenant_id,
            contact_id=command.contact_id,
            last_name=command.last_name,
            first_name=command.first_name,
            middle_name=command.middle_name,
        )
        return ContactDTO(
            id=contact.id.uuid,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            last_name=contact.contact_name.last_name,
            first_name=contact.contact_name.first_name,
            middle_name=contact.contact_name.middle_name,
        )
