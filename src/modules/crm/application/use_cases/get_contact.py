from __future__ import annotations

from src.modules.crm.application.dto import ContactDTO
from src.modules.crm.application.mappers import contact_to_dto
from src.modules.crm.application.queries import GetContactQuery
from src.modules.crm.domain.errors import ContactNotFoundError
from src.modules.crm.domain.repositories import ContactRepositoryProtocol
from src.modules.runtime_record.application import (
    ReadRuntimeValuesQuery,
    RuntimeRecordApplicationService,
)


class GetContactUseCase:
    def __init__(
        self,
        *,
        contact_repository: ContactRepositoryProtocol,
        runtime_record_service: RuntimeRecordApplicationService | None = None,
    ):
        self._contact_repository = contact_repository
        self._runtime_record_service = runtime_record_service

    async def execute(self, query: GetContactQuery) -> ContactDTO:
        contact = await self._contact_repository.get_by_id(query.contact_id)
        if contact is None:
            raise ContactNotFoundError(query.contact_id)
        custom_fields: dict[str, object | None] = {}
        if self._runtime_record_service is not None and query.tenant_id is not None:
            runtime_result = await self._runtime_record_service.read_values(
                ReadRuntimeValuesQuery(
                    tenant_id=query.tenant_id,
                    object_name_singular="contact",
                    record_id=query.contact_id,
                )
            )
            custom_fields = runtime_result.values
        return contact_to_dto(contact, custom_fields=custom_fields)


__all__ = ["GetContactUseCase"]
