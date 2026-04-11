from typing import Protocol

from src.modules.crm.application.contact.dto.contact_dto import ContactDTO
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.shared import EntityIdVO


class ContactQueryRepositoryProtocol(Protocol):
    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        contact_id: ContactIdVO,
    ) -> ContactDTO | None: ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> list[ContactDTO]: ...


__all__ = ["ContactQueryRepositoryProtocol"]
