from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SchemaDTO:
    id: UUID
    tenant_id: UUID
    created_at: str
    updated_at: str
    type: str
    schema_name: str
