from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RuntimeFieldDescriptionDTO:
    """DTO описания поля runtime-объекта из metadata schema_registry."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: dict[str, str]


@dataclass(frozen=True, slots=True)
class RuntimeObjectDescriptionDTO:
    """DTO описания runtime-объекта и его полей."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    fields: tuple[RuntimeFieldDescriptionDTO, ...]
