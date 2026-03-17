from __future__ import annotations

from src.modules.crm.application.dto import ContactDTO
from src.modules.crm.application.mappers import contact_to_dto
from src.modules.crm.application.queries import ListContactsQuery
from src.modules.crm.domain.repositories import ContactRepositoryProtocol


class ListContactsUseCase:
    def __init__(self, *, contact_repository: ContactRepositoryProtocol):
        self._contact_repository = contact_repository

    async def execute(self, query: ListContactsQuery) -> tuple[ContactDTO, ...]:
        _ = query
        contacts = await self._contact_repository.list()
        return tuple(contact_to_dto(contact) for contact in contacts)


__all__ = ["ListContactsUseCase"]
