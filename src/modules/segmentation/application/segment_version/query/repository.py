from typing import Protocol

from src.modules.segmentation.application.segment_version.dto import SegmentVersionDTO
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO
from src.modules.shared import EntityIdVO


class SegmentVersionQueryRepositoryProtocol(Protocol):
    """Query repository port for segment versions."""

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        segment_version_id: SegmentVersionIdVO,
    ) -> SegmentVersionDTO | None:
        """Returns one segment version read model."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentVersionDTO]:
        """Returns segment version page."""
        ...


__all__ = ["SegmentVersionQueryRepositoryProtocol"]
