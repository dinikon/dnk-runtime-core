from __future__ import annotations

from src.modules.crm.application.contact.ports import ContactRecord
from src.modules.crm.domain.contact.entity import ContactEntity
from src.modules.crm.domain.contact.value_objects import ContactIdVO, PersonNameVO
from src.modules.shared.domain.errors import ValidationError
from src.modules.runtime_record.application.contracts import RuntimeRecordPayload


class ContactRuntimeRecordMapper:
    def map_payload(
        self,
        payload: RuntimeRecordPayload,
    ) -> ContactRecord:
        name_payload = payload.system_values.get("name")
        if not isinstance(name_payload, dict):
            raise ValidationError(
                f"contact '{payload.record_id}' has invalid name payload."
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
                f"contact '{payload.record_id}' has invalid name payload: {exc}"
            ) from exc

        contact = ContactEntity(
            id=ContactIdVO.from_value(payload.record_id),
            name=person_name,
            contact_points=[],
        )
        return ContactRecord(
            contact=contact,
            custom_fields=dict(payload.custom_values),
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


__all__ = ["ContactRuntimeRecordMapper"]
