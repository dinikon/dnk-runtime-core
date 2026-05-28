from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class GetSegmentVersionQuery:
    """Query for one segment version."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    segment_version_id: SegmentVersionIdVO


__all__ = ["GetSegmentVersionQuery"]
