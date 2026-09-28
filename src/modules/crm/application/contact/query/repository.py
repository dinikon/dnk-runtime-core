from .list_available_contacts_query import ListAvailableContactsQuery
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.contact.dto import ContactDetailsDTO
from typing import Protocol

from src.modules.crm.application.contact.dto.contact_dto import ContactPageDTO
from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)


class ContactQueryRepositoryProtocol(Protocol):
    """Порт чтения страницы контактов."""

    async def list(self, query: ListContactsQuery) -> ContactPageDTO: ...

    async def get_details(
        self, tenant_id: EntityIdVO, identifier: ContactIdVO
    ) -> ContactDetailsDTO | None: ...

    async def list_available(
        self, query: ListAvailableContactsQuery
    ) -> ContactPageDTO | None: ...


__all__ = ["ContactQueryRepositoryProtocol"]
