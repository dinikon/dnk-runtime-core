from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)


@dataclass(slots=True, frozen=True)
class SegmentSnapshotMemberDTO:
    """Read model for Contact segment snapshot member."""

    id: UUID
    segment_snapshot_id: UUID
    contact_id: UUID
    position: int | None
    created_at: datetime
    contact: ContactSummaryDTO | None = None


__all__ = ["SegmentSnapshotMemberDTO"]
