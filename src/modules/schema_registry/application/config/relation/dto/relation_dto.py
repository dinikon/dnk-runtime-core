from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RelationDTO:
    """DTO relation metadata для config API."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    label: str | None
    relation_type: str
    source_object_id: UUID
    target_object_id: UUID
    source_object: str
    target_object: str
    source_relation_name: str
    target_relation_name: str
    owning_object_id: UUID | None
    owning_object: str | None
    fk_field_id: UUID | None
    fk_field: str | None
    referenced_object_id: UUID | None
    referenced_object: str | None
    referenced_field_id: UUID | None
    referenced_field: str | None
    relation_table_name: str | None
    source_join_column_name: str | None
    target_join_column_name: str | None
    on_delete: str
    is_required: bool
    is_unique: bool
    kind: str
    settings: dict[str, Any]


__all__ = ["RelationDTO"]
