from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class UpdateSegmentDefinitionCommand:
    """Command for updating Contact segment definition."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    name: str | None = None
    description: str | None = None
    description_provided: bool = False


__all__ = ["UpdateSegmentDefinitionCommand"]
