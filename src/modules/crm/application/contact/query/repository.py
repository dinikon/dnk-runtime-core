from typing import Protocol

from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


class ContactQueryRepositoryProtocol(Protocol):
    """Порт чтения контактов для CRM query use cases."""

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactDTO | None:
        """Возвращает контакт tenant по id или None."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> list[ContactDTO]:
        """Возвращает страницу контактов tenant."""
        ...


__all__ = ["ContactQueryRepositoryProtocol"]
