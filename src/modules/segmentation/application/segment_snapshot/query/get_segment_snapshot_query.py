from dataclasses import dataclass

from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class GetSegmentSnapshotQuery:
    """Query for loading one segment snapshot."""

    tenant_id: EntityIdVO
    segment_snapshot_id: SegmentSnapshotIdVO


__all__ = ["GetSegmentSnapshotQuery"]
