from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateSchemaCommand:
    tenant_id: UUID
    schema_name: str
    seed_path: str
