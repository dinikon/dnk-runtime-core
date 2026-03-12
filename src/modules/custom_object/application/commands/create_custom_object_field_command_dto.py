from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCustomObjectFieldCommandDTO:
    tenant_id: UUID
    object_name_singular: str
    field_type: str
    field_name: str
    label: str
    description: str | None = None
    icon: str | None = None
    is_active: bool = True
    is_unique: bool = False
    is_index: bool = False
    is_nullable: bool = True
    is_ui_read_only: bool = False
    is_searchable: bool = False
    options: dict[str, object] | None = None
    settings: dict[str, object] | None = None
    default_value: dict[str, object] | None = None
    relation_target_object_name: str | None = None
    relation_target_field_id: UUID | None = None


__all__ = ["CreateCustomObjectFieldCommandDTO"]
