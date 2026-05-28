from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_snapshot.value_object import (
    SegmentSnapshotIdVO,
    SegmentSnapshotStatusVO,
)
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO


@dataclass(frozen=True, slots=True)
class SegmentSnapshot:
    """Frozen segment audience snapshot."""

    segment_snapshot_id: SegmentSnapshotIdVO
    segment_id: SegmentIdVO
    segment_version_id: SegmentVersionIdVO
    status: SegmentSnapshotStatusVO
    member_count: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None


__all__ = ["SegmentSnapshot"]
