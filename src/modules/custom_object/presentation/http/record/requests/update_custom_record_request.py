from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UpdateCustomRecordRequestSchema(BaseModel):
    """Pydantic-схема обновления custom-object record."""

    object_id: UUID
    row_id: UUID
    values: dict[str, Any] = Field(default_factory=dict)


__all__ = ["UpdateCustomRecordRequestSchema"]
