from dataclasses import dataclass, field
from uuid import UUID

from src.modules.runtime_data.application.query.capabilities import (
    FieldFilterCapability,
    FieldSortCapability,
    disabled_filter_capability,
    disabled_sort_capability,
)


@dataclass(frozen=True, slots=True)
class ContactFieldOptionDTO:
    """DTO одного select-option в описании CRM-поля."""

    value: str
    label: str


@dataclass(frozen=True, slots=True)
class ContactFieldDescriptionDTO:
    """DTO описания CRM-поля."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: tuple[ContactFieldOptionDTO, ...]
    kind: str = "standard"
    filter: FieldFilterCapability = field(default_factory=disabled_filter_capability)
    sort: FieldSortCapability = field(default_factory=disabled_sort_capability)


@dataclass(frozen=True, slots=True)
class ContactObjectDescriptionDTO:
    """DTO описания CRM-объекта contact."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class ContactFieldsDescriptionDTO:
    """DTO описания CRM-модели контакта и ее полей."""

    object_description: ContactObjectDescriptionDTO
    fields: tuple[ContactFieldDescriptionDTO, ...]
