from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from src.modules.custom_object.presentation.http.field.requests.custom_field_request import (
    CustomFieldRequestSchema,
)


class CreateCustomFieldRequestSchema(BaseModel):
    """Pydantic-схема добавления поля custom object."""

    object_id: UUID
    field: CustomFieldRequestSchema


__all__ = ["CreateCustomFieldRequestSchema"]
