from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SegmentSnapshotMemberContactResponseSchema(BaseModel):
    """Contact summary returned with snapshot member."""

    id: UUID
    first_name: str
    last_name: str | None
    middle_name: str | None
    status: str | None


class SegmentSnapshotMemberResponseSchema(BaseModel):
    """Segment snapshot member response schema."""

    id: UUID
    segment_snapshot_id: UUID
    contact_id: UUID
    position: int | None
    created_at: datetime
    contact: SegmentSnapshotMemberContactResponseSchema | None = None


__all__ = [
    "SegmentSnapshotMemberContactResponseSchema",
    "SegmentSnapshotMemberResponseSchema",
]
