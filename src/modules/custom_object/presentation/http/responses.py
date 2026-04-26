from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CustomFieldResponseSchema(BaseModel):
    """HTTP response schema для поля custom object."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: dict[str, str]
    kind: str


class CustomObjectResponseSchema(BaseModel):
    """HTTP response schema для custom object."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    kind: str
    fields: list[CustomFieldResponseSchema]


class ListCustomObjectsResponseSchema(BaseModel):
    """HTTP response schema списка custom objects."""

    items: list[CustomObjectResponseSchema]
    count: int


class CustomRecordResponseSchema(BaseModel):
    """HTTP response schema custom-object record."""

    object_id: UUID
    row_id: UUID
    values: dict[str, Any]


class ListCustomRecordsResponseSchema(BaseModel):
    """HTTP response schema списка custom-object records."""

    items: list[CustomRecordResponseSchema]
    limit: int
    offset: int
    count: int


__all__ = [
    "CustomFieldResponseSchema",
    "CustomObjectResponseSchema",
    "CustomRecordResponseSchema",
    "ListCustomObjectsResponseSchema",
    "ListCustomRecordsResponseSchema",
]
