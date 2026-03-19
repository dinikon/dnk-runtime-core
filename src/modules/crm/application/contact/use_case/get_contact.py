from typing import Protocol

from modules.crm.application.contact.dto.contact_dto import ContactDTO
from modules.crm.application.contact.query.get_contact_query import GetContactQuery
from modules.crm.domain.contact.service import ContactService


class GetContactUseCaseProtocol(Protocol):

    async def __call__(self, query: GetContactQuery) -> ContactDTO: ...


class GetContactUseCase:
    def __init__(self, service: ContactService):
        self._service = service

    async def __call__(self, query: GetContactQuery) -> ContactDTO:
        contact = await self._service.get_contact(
            contact_id=query.contact_id,
        )
        return ContactDTO(
            id=contact.id.value,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            last_name=contact.contact_name.last_name,
            first_name=contact.contact_name.first_name,
            middle_name=contact.contact_name.middle_name,
        )
