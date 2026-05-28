from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SegmentVersionResponseSchema(BaseModel):
    """HTTP response for Contact segment version."""

    id: UUID
    segment_id: UUID
    version_number: int
    status: str
    config: dict[str, Any]
    config_checksum: str
    activated_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


__all__ = ["SegmentVersionResponseSchema"]
