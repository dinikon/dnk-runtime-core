from typing import Protocol

from src.modules.crm.application.contact.dto.contact_dto import ContactPageDTO
from src.modules.crm.application.contact.query.list_contacts_query import (
    ListContactsQuery,
)


class ContactQueryRepositoryProtocol(Protocol):
    """Порт чтения страницы контактов."""

    async def list(self, query: ListContactsQuery) -> ContactPageDTO: ...


__all__ = ["ContactQueryRepositoryProtocol"]
