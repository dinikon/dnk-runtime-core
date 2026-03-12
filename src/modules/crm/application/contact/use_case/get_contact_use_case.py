from __future__ import annotations

from src.modules.crm.application.contact.dto.get_contact_result_dto import (
    GetContactResultDTO,
)
from src.modules.crm.application.contact.queries.get_contact_query_dto import (
    GetContactQueryDTO,
)
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.value_objects import ContactIdVO, PersonNameVO
from src.modules.crm.domain.error import ContactNotFoundError
from src.modules.runtime_record.application.ports.storage import (
    RuntimeRecordReaderPort,
)
from src.modules.shared.domain.errors import ValidationError


class GetContactUseCase:
    def __init__(self, runtime_record_reader: RuntimeRecordReaderPort):
        self._runtime_record_reader = runtime_record_reader

    async def execute(self, dto: GetContactQueryDTO) -> GetContactResultDTO:
        record = await self._runtime_record_reader.get_record(
            tenant_id=dto.tenant_id,
            object_name_singular="contact",
            record_id=dto.contact_id,
        )
        if record is None:
            raise ContactNotFoundError(str(dto.contact_id))

        name_payload = record.system_values.get("name")
        if not isinstance(name_payload, dict):
            raise ValidationError(
                f"contact '{dto.contact_id}' has invalid name payload."
            )

        first_name = self._normalize_name_part(name_payload.get("first_name"))
        last_name = self._normalize_optional_name_part(name_payload.get("last_name"))
        middle_name = self._normalize_optional_name_part(name_payload.get("middle_name"))

        try:
            person_name = PersonNameVO(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
            )
        except ValueError as exc:
            raise ValidationError(
                f"contact '{dto.contact_id}' has invalid name payload: {exc}"
            ) from exc

        contact = ContactEntity(
            id=ContactIdVO.from_value(record.record_id),
            name=person_name,
            contact_points=[],
        )
        return GetContactResultDTO(
            contact=contact,
            custom_fields=record.custom_values,
        )

    @staticmethod
    def _normalize_name_part(value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _normalize_optional_name_part(value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


__all__ = [
    "GetContactUseCase",
]
