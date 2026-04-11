from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class DiffSchemaCommand:
    tenant_id: UUID
    seed_path: str
