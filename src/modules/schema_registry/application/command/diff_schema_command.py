from dataclasses import dataclass

from src.modules.shared import EntityIdVO

@dataclass(slots=True, frozen=True)
class DiffSchemaCommand:
    """Команда на применение diff между seed-спекой и runtime-схемой tenant."""

    tenant_id: EntityIdVO
    seed_path: str
