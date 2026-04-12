from dataclasses import dataclass

from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum


@dataclass(frozen=True, slots=True)
class RelationSeed:
    """Raw seed-описание relation между runtime-объектами."""

    name: str
    relation_type: str | RelationTypeEnum
    source_field: str
    target_object: str
    target_field: str = "id"
    on_delete: str = "restrict"
