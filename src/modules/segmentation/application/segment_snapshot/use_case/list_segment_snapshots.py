from typing import Protocol

from src.modules.segmentation.application.segment_snapshot.dto import SegmentSnapshotDTO
from src.modules.segmentation.application.segment_snapshot.query import (
    ListSegmentSnapshotsQuery,
    SegmentSnapshotQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_definition import (
    SegmentDefinitionCommandRepositoryProtocol,
    SegmentDefinitionNotFoundError,
)
from src.modules.segmentation.domain.segment_snapshot import InvalidSegmentSnapshotError


class ListSegmentSnapshotsUseCaseProtocol(Protocol):
    """Use case port for listing segment snapshots."""

    async def __call__(
        self,
        query: ListSegmentSnapshotsQuery,
    ) -> list[SegmentSnapshotDTO]:
        """Lists segment snapshots."""
        ...


class ListSegmentSnapshotsUseCase:
    """Lists Contact segment snapshots."""

    def __init__(
        self,
        *,
        segment_repository: SegmentDefinitionCommandRepositoryProtocol,
        repository: SegmentSnapshotQueryRepositoryProtocol,
    ) -> None:
        self._segment_repository = segment_repository
        self._repository = repository

    async def __call__(
        self,
        query: ListSegmentSnapshotsQuery,
    ) -> list[SegmentSnapshotDTO]:
        if query.limit < 1 or query.limit > 500:
            raise InvalidSegmentSnapshotError("Snapshot list limit must be 1..500.")
        if query.offset < 0:
            raise InvalidSegmentSnapshotError("Snapshot list offset must be >= 0.")
        segment = await self._segment_repository.load(
            tenant_id=query.tenant_id,
            segment_id=query.segment_id,
        )
        if segment is None:
            raise SegmentDefinitionNotFoundError(str(query.segment_id.uuid))
        return await self._repository.list(
            tenant_id=query.tenant_id,
            segment_id=query.segment_id,
            limit=query.limit,
            offset=query.offset,
        )


__all__ = [
    "ListSegmentSnapshotsUseCase",
    "ListSegmentSnapshotsUseCaseProtocol",
]
