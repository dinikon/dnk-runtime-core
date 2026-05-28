from typing import Protocol

from src.modules.segmentation.application.segment_snapshot.dto import (
    SegmentSnapshotDTO,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.shared import EntityIdVO


class SegmentSnapshotQueryRepositoryProtocol(Protocol):
    """Query repository port for segment snapshots."""

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
    ) -> SegmentSnapshotDTO | None:
        """Returns one segment snapshot read model."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentSnapshotDTO]:
        """Returns segment snapshot page."""
        ...


__all__ = ["SegmentSnapshotQueryRepositoryProtocol"]
