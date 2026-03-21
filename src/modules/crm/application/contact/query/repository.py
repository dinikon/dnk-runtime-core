from typing import Protocol

from src.modules.crm.application.contact.dto.contact_dto import ContactDTO


class ContactQueryRepositoryProtocol(Protocol):
    async def list(self, *, limit: int, offset: int) -> list[ContactDTO]: ...


__all__ = ["ContactQueryRepositoryProtocol"]
