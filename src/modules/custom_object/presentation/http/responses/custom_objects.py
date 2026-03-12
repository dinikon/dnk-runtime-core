from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CreateCustomObjectResponseSchema(BaseModel):
    id: UUID
    object_name_singular: str
    object_name_plural: str
    object_label_singular: str
    object_label_plural: str
    description: str | None
    icon: str | None
    shortcut: str | None
    is_active: bool
    is_ui_read_only: bool
    created_at: datetime
    updated_at: datetime


class CreateCustomObjectFieldResponseSchema(BaseModel):
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


class GetCustomObjectRecordResponseSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: UUID


__all__ = [
    "CreateCustomObjectFieldResponseSchema",
    "CreateCustomObjectResponseSchema",
    "GetCustomObjectRecordResponseSchema",
]
