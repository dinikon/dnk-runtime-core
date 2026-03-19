from dataclasses import dataclass

from src.modules.schema_registry.domain.field.value_object.field_type import FieldTypeVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class FieldSeed:
    id: EntityIdVO
    field_name: str
    field_type: FieldTypeVO
    label: str
    description: str
    is_nullable: bool
    options: dict[str, str]
    settings: dict[str, str]
