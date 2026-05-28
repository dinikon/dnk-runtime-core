from __future__ import annotations

from dataclasses import dataclass

from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.segmentation.domain.segment_snapshot_member.value_object import (
    SegmentSnapshotMemberIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class SegmentSnapshotMember:
    """Snapshot member represented by Contact id."""

    segment_snapshot_member_id: SegmentSnapshotMemberIdVO
    segment_snapshot_id: SegmentSnapshotIdVO
    contact_id: EntityIdVO
    position: int | None = None


__all__ = ["SegmentSnapshotMember"]
