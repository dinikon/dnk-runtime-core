from typing import Protocol

from modules.crm.domain.contact.value_object.contact_id import ContactIdVO
from src.modules.crm.domain.contact.entity import ContactEntity


class ContactQueryRepositoryProtocol(Protocol):

    async def get_by_id(self, *, contact_id: ContactIdVO) -> ContactEntity | None: ...

    async def list(self, *, limit: int, offset: int) -> list[ContactEntity]: ...


class ContactCommandRepositoryProtocol(Protocol):

    async def save(self, contact: ContactEntity) -> ContactEntity: ...

    async def delete(self, contact_id: ContactIdVO) -> None: ...
