from collections.abc import Sequence
from typing import Protocol

from src.modules.segmentation.domain.segment_snapshot import SegmentSnapshotIdVO
from src.modules.shared import EntityIdVO


class SegmentSnapshotMemberCommandRepositoryProtocol(Protocol):
    """Command repository port for segment snapshot members."""

    async def add_members(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
        contact_ids: Sequence[EntityIdVO],
        start_position: int = 0,
    ) -> int:
        """Adds snapshot members and returns stored unique member count."""
        ...

    async def delete_for_failed_snapshot(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_snapshot_id: SegmentSnapshotIdVO,
    ) -> None:
        """Deletes members for a snapshot that failed during creation."""
        ...


__all__ = ["SegmentSnapshotMemberCommandRepositoryProtocol"]
