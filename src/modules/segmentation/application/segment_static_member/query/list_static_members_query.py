from dataclasses import dataclass

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ListStaticMembersQuery:
    """Query for static Contact segment members."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    limit: int = 50
    offset: int = 0
    include_contact_summary: bool = True


__all__ = ["ListStaticMembersQuery"]
