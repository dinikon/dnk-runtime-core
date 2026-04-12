from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class CreateSchemaCommand:
    """Команда на первичное создание runtime-схемы tenant из seed-модуля."""

    tenant_id: UUID
    schema_name: str
    seed_path: str
