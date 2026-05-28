from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SegmentDefinitionDTO:
    """Read model for Contact segment definition."""

    id: UUID
    name: str
    segment_kind: str
    status: str
    description: str | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


__all__ = ["SegmentDefinitionDTO"]
