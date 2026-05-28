from typing import Protocol

from src.modules.segmentation.domain.segment_definition.entity import SegmentDefinition
from src.modules.segmentation.domain.segment_definition.value_object import SegmentIdVO
from src.modules.shared import EntityIdVO


class SegmentDefinitionCommandRepositoryProtocol(Protocol):
    """Command repository port for segment definitions."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        segment_id: SegmentIdVO,
    ) -> SegmentDefinition | None:
        """Loads a segment definition by id."""
        ...


__all__ = ["SegmentDefinitionCommandRepositoryProtocol"]
