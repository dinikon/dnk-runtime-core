from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ListObjectRelationsRequestSchema(BaseModel):
    """Pydantic-схема списка relations object."""

    object_id: UUID


__all__ = ["ListObjectRelationsRequestSchema"]
