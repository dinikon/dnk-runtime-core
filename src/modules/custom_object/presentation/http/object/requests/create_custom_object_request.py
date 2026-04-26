from __future__ import annotations

from pydantic import BaseModel, Field

from src.modules.custom_object.presentation.http.field.requests import (
    CustomFieldRequestSchema,
)


class CreateCustomObjectRequestSchema(BaseModel):
    """Pydantic-схема создания custom object."""

    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str = ""
    fields: list[CustomFieldRequestSchema] = Field(default_factory=list)


__all__ = ["CreateCustomObjectRequestSchema"]
