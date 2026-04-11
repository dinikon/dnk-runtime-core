from typing import Protocol

from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


class ContactCommandRepositoryProtocol(Protocol):
    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactEntity | None: ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        contact: ContactEntity,
    ) -> ContactEntity: ...

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> None: ...
