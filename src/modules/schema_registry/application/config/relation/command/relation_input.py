from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO


@dataclass(frozen=True, slots=True)
class RelationInput:
    """Input для создания custom relation через config API."""

    name: str
    relation_type: str
    source_object_id: RuntimeObjectIdVO
    target_object_id: RuntimeObjectIdVO
    label: str | None = None
    owning_object_id: RuntimeObjectIdVO | None = None
    fk_field_name: str | None = None
    referenced_object_id: RuntimeObjectIdVO | None = None
    referenced_field_name: str = "id"
    source_relation_name: str | None = None
    target_relation_name: str | None = None
    relation_table_name: str | None = None
    source_join_column_name: str | None = None
    target_join_column_name: str | None = None
    on_delete: str = "restrict"
    is_required: bool = False
    settings: dict[str, Any] = field(default_factory=dict)


__all__ = ["RelationInput"]
