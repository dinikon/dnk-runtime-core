from dataclasses import dataclass

from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateSchemaCommand:
    """Команда на первичное создание runtime-схемы tenant из seed-модуля."""

    tenant_id: EntityIdVO
    schema_name: str
    seed_path: str
