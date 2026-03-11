from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class FieldMetadataEntity:
    id: UUID
    tenant_id: UUID
    object_metadata_id: UUID
    type: str
    field_name: str
    label: str
    defaultValue: str | None
    description: str | None
