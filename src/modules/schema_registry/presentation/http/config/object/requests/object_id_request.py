from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ObjectIdRequestSchema(BaseModel):
    """Pydantic-схема тела запроса с object_id."""

    object_id: UUID


__all__ = ["ObjectIdRequestSchema"]
