from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCustomObjectFieldResultDTO:
    id: UUID
    object_id: UUID
    field_type: str
    field_name: str
    label: str
    description: str | None
    icon: str | None
    is_active: bool
    is_unique: bool
    is_index: bool
    is_nullable: bool
    is_ui_read_only: bool
    is_searchable: bool
    created_at: datetime
    updated_at: datetime


__all__ = ["CreateCustomObjectFieldResultDTO"]
