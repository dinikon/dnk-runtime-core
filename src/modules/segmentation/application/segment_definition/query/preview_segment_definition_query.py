from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class PreviewSegmentDefinitionQuery:
    """Query for previewing a segment definition."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    segment_version_id: SegmentVersionIdVO | None = None
    limit: int = 50
    offset: int = 0
    include_contact_summary: bool = True


__all__ = ["PreviewSegmentDefinitionQuery"]
