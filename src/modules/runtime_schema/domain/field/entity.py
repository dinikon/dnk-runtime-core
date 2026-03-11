from dataclasses import dataclass
from datetime import datetime

from modules.runtime_schema.domain.field.value_object import (
    FieldIdVO,
    FieldTypeVO,
    FieldName,
)
from modules.runtime_schema.domain.object.value_object import ObjectIdVO
from modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class FieldMetadataEntity:
    id: FieldIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO
    object_metadata_id: ObjectIdVO

    field_type: FieldTypeVO
    field_name: FieldName

    label: str
    description: str | None
    icon: str | None

    is_system: bool
    is_custom: bool
    is_active: bool

    is_unique: bool
    is_index: bool
    is_nullable: bool

    is_ui_read_only: bool
    is_searchable: bool

    options: dict[str, object] | None
    settings: dict[str, object] | None
    default_value: dict[str, object] | None

    relation_target_object_id: ObjectIdVO | None
    relation_target_field_id: FieldIdVO | None
