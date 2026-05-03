from __future__ import annotations

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


__all__ = ["CustomFieldRequestSchema"]
