from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from src.modules.crm.application.contact_points.port import ContactPointInputDTO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class EmailInput(BaseModel):
    """Входная строка email; идентификаторы принадлежат текущему владельцу."""

    model_config = ConfigDict(extra="forbid")
    value: str
    binding_id: UUID | None = None
    label_id: UUID | None = None


class PhoneInput(EmailInput):
    """Телефон всегда передаётся с явно выбранной страной."""

    country_code: str


class ContactPointsRequest(BaseModel):
    """Массивы опциональны, но явный null вместо списка запрещён."""

    model_config = ConfigDict(extra="forbid")
    phones: list[PhoneInput] = Field(default_factory=list)
    emails: list[EmailInput] = Field(default_factory=list)


class ContactPointResponse(BaseModel):
    """HTTP-строка телефонного или email списка."""

    binding_id: UUID
    contact_point_id: UUID
    value: str
    label_id: UUID | None
    country_code: str | None


def contact_point_inputs(payload, uuid_generator):
    """Сохраняет omitted/empty семантику и выдаёт candidate UUID на HTTP boundary."""
    result = {}
    for field in ("phones", "emails"):
        if field not in payload.model_fields_set:
            result[field] = None
            continue
        result[field] = tuple(
            ContactPointInputDTO(
                candidate_point_id=EntityIdVO.from_value(uuid_generator.new()),
                candidate_binding_id=EntityIdVO.from_value(uuid_generator.new()),
                value=row.value,
                binding_id=(
                    EntityIdVO.from_value(row.binding_id) if row.binding_id else None
                ),
                label_id=EntityIdVO.from_value(row.label_id) if row.label_id else None,
                country_code=getattr(row, "country_code", None),
            )
            for row in getattr(payload, field)
        )
    return result


__all__ = ["ContactPointsRequest", "ContactPointResponse", "contact_point_inputs"]
