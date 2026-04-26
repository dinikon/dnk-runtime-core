from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CustomFieldRequestSchema(BaseModel):
    """Pydantic-схема поля custom object."""

    field_name: str
    type: str
    label: str
    description: str = ""
    is_nullable: bool = True
    default_value: str | None = None
    options: dict[str, str] = Field(default_factory=dict)
    settings: dict[str, str] = Field(default_factory=dict)


class CreateCustomObjectRequestSchema(BaseModel):
    """Pydantic-схема создания custom object."""

    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str = ""
    fields: list[CustomFieldRequestSchema] = Field(default_factory=list)


class ObjectIdRequestSchema(BaseModel):
    """Pydantic-схема тела запроса с object_id."""

    object_id: UUID


class DeleteCustomFieldRequestSchema(BaseModel):
    """Pydantic-схема удаления поля custom object."""

    object_id: UUID
    field_id: UUID


class CreateCustomFieldRequestSchema(BaseModel):
    """Pydantic-схема добавления поля custom object."""

    object_id: UUID
    field: CustomFieldRequestSchema


class CreateCustomRecordRequestSchema(BaseModel):
    """Pydantic-схема создания custom-object record."""

    object_id: UUID
    values: dict[str, Any] = Field(default_factory=dict)


class CustomRecordByIdRequestSchema(BaseModel):
    """Pydantic-схема операции над custom-object record."""

    object_id: UUID
    row_id: UUID


class ListCustomRecordsRequestSchema(BaseModel):
    """Pydantic-схема списка custom-object records."""

    object_id: UUID
    filter: dict[str, Any] | None = None
    sort: dict[str, str] | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class UpdateCustomRecordRequestSchema(BaseModel):
    """Pydantic-схема обновления custom-object record."""

    object_id: UUID
    row_id: UUID
    values: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "CreateCustomFieldRequestSchema",
    "CreateCustomObjectRequestSchema",
    "CreateCustomRecordRequestSchema",
    "CustomFieldRequestSchema",
    "CustomRecordByIdRequestSchema",
    "DeleteCustomFieldRequestSchema",
    "ListCustomRecordsRequestSchema",
    "ObjectIdRequestSchema",
    "UpdateCustomRecordRequestSchema",
]
