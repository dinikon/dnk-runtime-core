from typing import Protocol

from src.modules.segmentation.domain.segment_snapshot.entity import SegmentSnapshot
from src.modules.segmentation.domain.segment_snapshot.value_object import (
    SegmentSnapshotIdVO,
)
from src.modules.shared import EntityIdVO


class SegmentSnapshotCommandRepositoryProtocol(Protocol):
    """Command repository port for segment snapshots."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
    ) -> SegmentSnapshot | None:
        """Loads a segment snapshot by id."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        snapshot: SegmentSnapshot,
    ) -> SegmentSnapshot:
        """Creates or updates a segment snapshot."""
        ...


__all__ = ["SegmentSnapshotCommandRepositoryProtocol"]
