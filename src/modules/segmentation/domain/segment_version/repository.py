from datetime import datetime
from typing import Protocol

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version.entity import SegmentVersion
from src.modules.segmentation.domain.segment_version.value_object import (
    SegmentVersionIdVO,
)
from src.modules.shared import EntityIdVO


class SegmentVersionCommandRepositoryProtocol(Protocol):
    """Command repository port for segment versions."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_version_id: SegmentVersionIdVO,
    ) -> SegmentVersion | None:
        """Loads a segment version by id."""
        ...

    async def get_active(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentVersion | None:
        """Returns active version for a segment."""
        ...

    async def get_next_version_number(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> int:
        """Returns next version number for a segment."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        version: SegmentVersion,
    ) -> SegmentVersion:
        """Creates or updates a segment version."""
        ...

    async def archive_active_versions(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
        now: datetime,
    ) -> None:
        """Archives active versions for a segment."""
        ...


__all__ = ["SegmentVersionCommandRepositoryProtocol"]
