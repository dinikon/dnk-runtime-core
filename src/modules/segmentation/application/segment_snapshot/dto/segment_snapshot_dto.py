from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True, frozen=True)
class SegmentSnapshotDTO:
    """Read model for Contact segment snapshot."""

    id: UUID
    segment_id: UUID
    segment_version_id: UUID
    status: str
    member_count: int
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


__all__ = ["SegmentSnapshotDTO"]
