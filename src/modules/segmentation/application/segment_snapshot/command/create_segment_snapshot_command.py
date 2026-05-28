from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version import SegmentVersionIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateSegmentSnapshotCommand:
    """Command for creating a Contact segment snapshot."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    segment_version_id: SegmentVersionIdVO | None = None


__all__ = ["CreateSegmentSnapshotCommand"]
