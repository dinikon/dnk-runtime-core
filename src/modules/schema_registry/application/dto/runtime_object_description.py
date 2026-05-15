from dataclasses import dataclass
from typing import Any
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
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class RuntimeObjectDescriptionDTO:
    """DTO описания runtime-объекта и его полей."""

    id: UUID
    singular_label: str
    plural_label: str
    description: str
    fields: tuple[RuntimeFieldDescriptionDTO, ...]
    relations: tuple["RuntimeRelationDescriptionDTO", ...] = ()
    kind: str = "standard"


@dataclass(frozen=True, slots=True)
class RuntimeRelationDescriptionDTO:
    """DTO описания relation runtime-объекта."""

    id: str
    name: str
    label: str | None
    relation_type: str
    source_object: str
    target_object: str
    source_relation_name: str
    target_relation_name: str
    owning_object: str | None
    fk_field: str | None
    referenced_object: str | None
    referenced_field: str | None
    relation_table_name: str | None
    source_join_column_name: str | None
    target_join_column_name: str | None
    is_collection: bool
    is_virtual: bool
    is_unique: bool
    is_required: bool
    kind: str
    settings: dict[str, Any]
