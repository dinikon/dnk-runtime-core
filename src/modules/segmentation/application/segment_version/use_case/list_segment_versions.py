from typing import Protocol

from src.modules.segmentation.application.segment_version.dto import (
    SegmentVersionDTO,
)
from src.modules.segmentation.application.segment_version.query import (
    ListSegmentVersionsQuery,
    SegmentVersionQueryRepositoryProtocol,
)


class ListSegmentVersionsUseCaseProtocol(Protocol):
    """Use case port for listing segment versions."""

    async def __call__(
        self,
        query: ListSegmentVersionsQuery,
    ) -> list[SegmentVersionDTO]:
        """Returns segment version page."""
        ...


class ListSegmentVersionsUseCase:
    """Returns Contact segment versions."""

    def __init__(self, repository: SegmentVersionQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(
        self,
        query: ListSegmentVersionsQuery,
    ) -> list[SegmentVersionDTO]:
        return await self._repository.list(
            tenant_id=query.tenant_id,
            segment_id=query.segment_id,
            limit=query.limit,
            offset=query.offset,
        )


__all__ = [
    "ListSegmentVersionsUseCase",
    "ListSegmentVersionsUseCaseProtocol",
]
