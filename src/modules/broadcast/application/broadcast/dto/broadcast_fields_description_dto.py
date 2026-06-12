from dataclasses import dataclass, field
from uuid import UUID

from src.modules.runtime_data.application.query.capabilities.field_query_capability import (
    FieldFilterCapability,
    FieldSortCapability,
    disabled_filter_capability,
    disabled_sort_capability,
)


@dataclass(frozen=True, slots=True)
class BroadcastFieldOptionDTO:
    """DTO одного select-option в описании broadcast-поля."""

    value: str
    label: str


@dataclass(frozen=True, slots=True)
class BroadcastFieldDescriptionDTO:
    """DTO описания одного поля broadcast."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: tuple[BroadcastFieldOptionDTO, ...]
    kind: str = "standard"
    filter: FieldFilterCapability = field(default_factory=disabled_filter_capability)
    sort: FieldSortCapability = field(default_factory=disabled_sort_capability)


@dataclass(frozen=True, slots=True)
class BroadcastObjectDescriptionDTO:
    """DTO описания объекта broadcast."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class BroadcastFieldsDescriptionDTO:
    """DTO описания broadcast-модели и ее полей."""

    object_description: BroadcastObjectDescriptionDTO
    fields: tuple[BroadcastFieldDescriptionDTO, ...]


__all__ = [
    "BroadcastFieldDescriptionDTO",
    "BroadcastFieldOptionDTO",
    "BroadcastFieldsDescriptionDTO",
    "BroadcastObjectDescriptionDTO",
]
