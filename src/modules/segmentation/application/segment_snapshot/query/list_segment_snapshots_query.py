from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class ListSegmentSnapshotsQuery:
    """Query for listing segment snapshots."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    limit: int = 50
    offset: int = 0


__all__ = ["ListSegmentSnapshotsQuery"]
