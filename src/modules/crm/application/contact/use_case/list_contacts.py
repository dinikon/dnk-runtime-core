from typing import Protocol

from modules.crm.application.contact.dto.contact_dto import ContactDTO
from modules.crm.application.contact.query.list_contacts_query import ListContactsQuery
from modules.crm.domain.contact.service import ContactService


class ListContactsUseCaseProtocol(Protocol):
    async def __call__(self, query: ListContactsQuery) -> list[ContactDTO]: ...


class ListContactsUseCase:
    def __init__(self, service: ContactService):
        self._service = service

    async def __call__(self, query: ListContactsQuery) -> list[ContactDTO]:
        contacts = await self._service.list_contacts(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
        )
        return [
            ContactDTO(
                id=contact.id.value,
                tenant_id=contact.tenant_id,
                created_at=contact.created_at,
                updated_at=contact.updated_at,
                last_name=contact.contact_name.last_name,
                first_name=contact.contact_name.first_name,
                middle_name=contact.contact_name.middle_name,
            )
            for contact in contacts
        ]
