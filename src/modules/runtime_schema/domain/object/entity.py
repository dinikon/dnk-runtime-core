from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from modules.runtime_schema.domain.object.value_object import (
    ObjectIdVO,
    ObjectNameVO,
    ObjectLabelVO,
)
from modules.runtime_schema.domain.source.value_object import DataSourceIdVO
from modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ObjectMetadataEntity:
    id: ObjectIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO
    data_source_id: DataSourceIdVO

    object_name: ObjectNameVO
    object_label: ObjectLabelVO

    description: str | None
    icon: str | None
    shortcut: str | None

    is_remote: bool
    is_system: bool
    is_custom: bool
    is_active: bool
    is_ui_read_only: bool

    duplicate_criteria: dict[str, object] | None = field(default_factory=dict)


__all__ = ["ObjectMetadataEntity"]
