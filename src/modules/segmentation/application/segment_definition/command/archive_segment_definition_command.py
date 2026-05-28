from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ArchiveSegmentDefinitionCommand:
    """Command for archiving Contact segment definition."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO


__all__ = ["ArchiveSegmentDefinitionCommand"]
