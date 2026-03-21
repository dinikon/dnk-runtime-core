from typing import Protocol

from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.shared import EntityIdVO


class ContactCommandRepositoryProtocol(Protocol):
    async def load(self, *, contact_id: EntityIdVO) -> ContactEntity | None: ...

    async def save(self, *, contact: ContactEntity) -> ContactEntity: ...

    async def delete(self, *, contact_id: EntityIdVO) -> None: ...
