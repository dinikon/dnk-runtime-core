from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class DeleteCustomFieldRequestSchema(BaseModel):
    """Pydantic-схема удаления поля custom object."""

    object_id: UUID
    field_id: UUID


__all__ = ["DeleteCustomFieldRequestSchema"]
