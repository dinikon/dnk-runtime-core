from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class RemoveStaticMemberCommand:
    """Command for removing Contact from a static segment."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    contact_id: EntityIdVO


__all__ = ["RemoveStaticMemberCommand"]
