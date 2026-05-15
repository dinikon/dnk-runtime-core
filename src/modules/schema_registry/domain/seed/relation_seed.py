from dataclasses import dataclass
from typing import Literal

from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum

RelationKindValue = Literal["system", "standard", "custom"]
RelationOnDeleteValue = Literal["restrict", "cascade", "set_null", "no_action"]


@dataclass(frozen=True, slots=True)
class RelationSeed:
    """Raw seed-описание relation между runtime-объектами."""

    name: str
    relation_type: str | RelationTypeEnum

    source_object: str | None = None
    target_object: str | None = None

    owning_object: str | None = None
    fk_field: str | None = None

    referenced_object: str | None = None
    referenced_field: str = "id"

    source_relation_name: str | None = None
    target_relation_name: str | None = None

    relation_table_name: str | None = None
    source_join_column_name: str | None = None
    target_join_column_name: str | None = None

    on_delete: RelationOnDeleteValue = "restrict"
    is_required: bool = False
    kind: RelationKindValue = "standard"
    settings: dict[str, str] | None = None
