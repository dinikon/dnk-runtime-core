from typing import Protocol

from src.modules.segmentation.application.segment_version.dto import (
    SegmentVersionDTO,
)
from src.modules.segmentation.application.segment_version.query import (
    GetSegmentVersionQuery,
    SegmentVersionQueryRepositoryProtocol,
)
from src.modules.segmentation.domain.segment_version import SegmentVersionNotFoundError


class GetSegmentVersionUseCaseProtocol(Protocol):
    """Use case port for getting segment version."""

    async def __call__(
        self,
        query: GetSegmentVersionQuery,
    ) -> SegmentVersionDTO:
        """Returns segment version."""
        ...


class GetSegmentVersionUseCase:
    """Returns Contact segment version."""

    def __init__(self, repository: SegmentVersionQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(
        self,
        query: GetSegmentVersionQuery,
    ) -> SegmentVersionDTO:
        dto = await self._repository.get(
            tenant_id=query.tenant_id,
            segment_id=query.segment_id,
            segment_version_id=query.segment_version_id,
        )
        if dto is None:
            raise SegmentVersionNotFoundError(str(query.segment_version_id))
        return dto


__all__ = [
    "GetSegmentVersionUseCase",
    "GetSegmentVersionUseCaseProtocol",
]
