from typing import Protocol

from src.modules.crm.domain.contact.entity import Contact
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ContactRepositoryProtocol(Protocol):
    """Порт командного хранения контактов."""

    async def get(
        self,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
        *,
        for_update: bool = False,
    ) -> Contact: ...

    async def add(self, tenant_id: EntityIdVO, contact: Contact) -> None: ...

    async def save(self, tenant_id: EntityIdVO, contact: Contact) -> None: ...

    async def delete(self, tenant_id: EntityIdVO, contact_id: ContactIdVO) -> None: ...


__all__ = ["ContactRepositoryProtocol"]
