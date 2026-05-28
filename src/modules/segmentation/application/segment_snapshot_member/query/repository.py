from typing import Protocol

from src.modules.segmentation.application.segment_snapshot_member.dto import (
    SegmentSnapshotMemberDTO,
)
from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.shared import EntityIdVO


class SegmentSnapshotMemberQueryRepositoryProtocol(Protocol):
    """Query repository port for segment snapshot members."""

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentSnapshotMemberDTO]:
        """Returns segment snapshot member page."""
        ...


__all__ = ["SegmentSnapshotMemberQueryRepositoryProtocol"]
