from dataclasses import dataclass
from typing import Any, Mapping

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_static_member import (
    SegmentStaticMemberSourceTypeVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class AddStaticMemberCommand:
    """Command for adding Contact to a static segment."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    contact_id: EntityIdVO
    source_type: SegmentStaticMemberSourceTypeVO = (
        SegmentStaticMemberSourceTypeVO.MANUAL
    )
    metadata: Mapping[str, Any] | None = None


__all__ = ["AddStaticMemberCommand"]
