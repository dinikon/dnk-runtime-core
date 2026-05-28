from typing import Protocol

from src.modules.segmentation.application.segment_snapshot.dto import SegmentSnapshotDTO
from src.modules.segmentation.application.segment_snapshot.query import (
    GetSegmentSnapshotQuery,
    SegmentSnapshotQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_snapshot import (
    SegmentSnapshotNotFoundError,
)


class GetSegmentSnapshotUseCaseProtocol(Protocol):
    """Use case port for loading one segment snapshot."""

    async def __call__(self, query: GetSegmentSnapshotQuery) -> SegmentSnapshotDTO:
        """Returns one segment snapshot."""
        ...


class GetSegmentSnapshotUseCase:
    """Loads one Contact segment snapshot."""

    def __init__(
        self,
        *,
        repository: SegmentSnapshotQueryRepositoryProtocol,
    ) -> None:
        self._repository = repository

    async def __call__(self, query: GetSegmentSnapshotQuery) -> SegmentSnapshotDTO:
        snapshot = await self._repository.get(
            tenant_id=query.tenant_id,
            segment_snapshot_id=query.segment_snapshot_id,
        )
        if snapshot is None:
            raise SegmentSnapshotNotFoundError(str(query.segment_snapshot_id.uuid))
        return snapshot


__all__ = [
    "GetSegmentSnapshotUseCase",
    "GetSegmentSnapshotUseCaseProtocol",
]
