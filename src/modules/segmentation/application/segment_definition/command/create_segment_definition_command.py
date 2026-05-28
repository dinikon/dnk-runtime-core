from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentKindVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateSegmentDefinitionCommand:
    """Command for creating Contact segment definition."""

    tenant_id: EntityIdVO
    name: str
    segment_kind: SegmentKindVO = SegmentKindVO.STATIC
    description: str | None = None


__all__ = ["CreateSegmentDefinitionCommand"]
