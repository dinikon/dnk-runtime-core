from typing import Protocol

from src.modules.segmentation.application.segment_definition.dto import (
    SegmentDefinitionDTO,
)
from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


class SegmentDefinitionQueryRepositoryProtocol(Protocol):
    """Query repository port for segment definitions."""

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinitionDTO | None:
        """Returns one segment definition read model."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
    ) -> list[SegmentDefinitionDTO]:
        """Returns segment definition page."""
        ...


__all__ = ["SegmentDefinitionQueryRepositoryProtocol"]
