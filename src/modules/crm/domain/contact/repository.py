from typing import Protocol

from src.modules.shared import EntityIdVO
from src.modules.crm.domain.contact.entity import ContactEntity


class ContactQueryRepositoryProtocol(Protocol):

    async def get_by_id(self, *, contact_id: EntityIdVO) -> ContactEntity | None: ...

    async def list(self, *, limit: int, offset: int) -> list[ContactEntity]: ...


class ContactCommandRepositoryProtocol(Protocol):

    async def save(self, contact: ContactEntity) -> ContactEntity: ...

    async def delete(self, contact_id: EntityIdVO) -> None: ...
