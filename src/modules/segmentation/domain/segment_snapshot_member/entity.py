from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.segmentation.domain.segment_snapshot_member.error import (
    InvalidSegmentSnapshotMemberError,
)
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

    @classmethod
    def create(
        cls,
        *,
        segment_snapshot_member_id: SegmentSnapshotMemberIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
        contact_id: EntityIdVO,
        position: int | None = None,
    ) -> Self:
        """Creates snapshot member from already prepared value objects."""
        if position is not None and position < 0:
            raise InvalidSegmentSnapshotMemberError(
                "Segment snapshot member position must be >= 0."
            )
        return cls(
            segment_snapshot_member_id=segment_snapshot_member_id,
            segment_snapshot_id=segment_snapshot_id,
            contact_id=contact_id,
            position=position,
        )


__all__ = ["SegmentSnapshotMember"]
