from typing import Protocol

from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.application.contact.query.get_contact_query import GetContactQuery
from src.modules.crm.application.contact.query.repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.domain.contact.error import ContactNotFoundError


class GetContactUseCaseProtocol(Protocol):
    async def __call__(self, query: GetContactQuery) -> ContactDTO: ...


class GetContactUseCase:
    def __init__(self, query_repository: ContactQueryRepositoryProtocol):
        self._query_repository = query_repository

    async def __call__(self, query: GetContactQuery) -> ContactDTO:
        contact = await self._query_repository.get_by_id(
            tenant_id=query.tenant_id,
            contact_id=query.contact_id,
        )
        if contact is None:
            raise ContactNotFoundError(str(query.contact_id))
        return contact
