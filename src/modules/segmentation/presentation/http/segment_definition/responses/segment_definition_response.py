from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SegmentDefinitionResponseSchema(BaseModel):
    """HTTP response for Contact segment definition."""

    id: UUID
    name: str
    segment_kind: str
    status: str
    description: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


__all__ = ["SegmentDefinitionResponseSchema"]
