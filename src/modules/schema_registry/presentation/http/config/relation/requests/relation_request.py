from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RelationRequestSchema(BaseModel):
    """Pydantic-схема custom relation input."""

    name: str
    relation_type: str
    source_object_id: UUID
    target_object_id: UUID
    label: str | None = None
    owning_object_id: UUID | None = None
    fk_field_name: str | None = None
    referenced_object_id: UUID | None = None
    referenced_field_name: str = "id"
    source_relation_name: str | None = None
    target_relation_name: str | None = None
    relation_table_name: str | None = None
    source_join_column_name: str | None = None
    target_join_column_name: str | None = None
    on_delete: str = "restrict"
    is_required: bool = False
    settings: dict[str, Any] = Field(default_factory=dict)


__all__ = ["RelationRequestSchema"]
