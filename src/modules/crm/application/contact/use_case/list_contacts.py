from typing import Protocol

from modules.crm.application.contact.dto.contact_dto import ContactDTO
from modules.crm.application.contact.query.list_contacts_query import ListContactsQuery
from modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)


class ListContactsUseCaseProtocol(Protocol):
    async def __call__(self, query: ListContactsQuery) -> list[ContactDTO]: ...


class ListContactsUseCase:
    def __init__(self, query_repository: ContactQueryRepositoryProtocol):
        self._query_repository = query_repository

    async def __call__(self, query: ListContactsQuery) -> list[ContactDTO]:
        return await self._query_repository.list(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
        )
