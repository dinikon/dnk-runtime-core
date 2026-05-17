from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ListCustomRecordsRequestSchema(BaseModel):
    """Pydantic-схема списка custom-object records."""

    object_id: UUID
    filter: dict[str, Any] | None = None
    sort: list[dict[str, Any]] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


__all__ = ["ListCustomRecordsRequestSchema"]
