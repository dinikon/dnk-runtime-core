from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class DiffSchemaCommand:
    """Команда на применение diff между seed-спекой и runtime-схемой tenant."""

    tenant_id: UUID
    seed_path: str
