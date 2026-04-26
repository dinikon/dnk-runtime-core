from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class CustomRecordByIdRequestSchema(BaseModel):
    """Pydantic-схема операции над custom-object record."""

    object_id: UUID
    row_id: UUID


__all__ = ["CustomRecordByIdRequestSchema"]
