from __future__ import annotations

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


__all__ = ["CustomFieldResponseSchema"]
