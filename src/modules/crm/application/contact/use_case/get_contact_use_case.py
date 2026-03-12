from __future__ import annotations

from src.modules.crm.application.contact.dto import GetContactResultDTO
from src.modules.crm.application.contact.ports import (
    ContactRecordRepositoryPort,
    GetContactRecordQuery,
)
from src.modules.crm.application.contact.queries import GetContactQueryDTO
from src.modules.crm.domain.error import ContactNotFoundError


class GetContactUseCase:
    def __init__(self, repository: ContactRecordRepositoryPort):
        self._repository = repository

    async def execute(self, dto: GetContactQueryDTO) -> GetContactResultDTO:
        record = await self._repository.get_by_id(
            GetContactRecordQuery(
                tenant_id=dto.tenant_id,
                contact_id=dto.contact_id,
            )
        )
        if record is None:
            raise ContactNotFoundError(str(dto.contact_id))
        return GetContactResultDTO(
            contact=record.contact,
            custom_fields=record.custom_fields,
        )


__all__ = [
    "GetContactUseCase",
]
