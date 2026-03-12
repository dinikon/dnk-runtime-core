from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CreateCustomObjectRequestSchema(BaseModel):
    object_name_singular: str
    object_name_plural: str | None = None
    object_label_singular: str | None = None
    object_label_plural: str | None = None
    description: str | None = None
    icon: str | None = None
    shortcut: str | None = None
    is_active: bool = True
    is_ui_read_only: bool = False


class CreateCustomObjectFieldRequestSchema(BaseModel):
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


__all__ = [
    "CreateCustomObjectFieldRequestSchema",
    "CreateCustomObjectRequestSchema",
]
