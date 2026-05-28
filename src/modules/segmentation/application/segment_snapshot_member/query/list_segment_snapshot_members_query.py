from dataclasses import dataclass

from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListSegmentSnapshotMembersQuery:
    """Query for listing segment snapshot members."""

    tenant_id: EntityIdVO
    segment_snapshot_id: SegmentSnapshotIdVO
    limit: int = 50
    offset: int = 0
    include_contact_summary: bool = True


__all__ = ["ListSegmentSnapshotMembersQuery"]
