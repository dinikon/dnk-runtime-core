from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from modules.runtime_schema.domain.object.value_object import ObjectIdVO
from modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(slots=True)
class ObjectMetadataEntity:
    id: ObjectIdVO
    created_at: datetime
    updated_at: datetime
    tenant_id: EntityIdVO


__all__ = ["ObjectMetadataEntity"]
