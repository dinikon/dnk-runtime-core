from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_static_member.value_object import (
    SegmentStaticMemberIdVO,
    SegmentStaticMemberSourceTypeVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class SegmentStaticMember:
    """Static segment member represented by Contact id."""

    segment_static_member_id: SegmentStaticMemberIdVO
    segment_id: SegmentIdVO
    contact_id: EntityIdVO
    source_type: SegmentStaticMemberSourceTypeVO
    metadata: dict[str, Any] | None = None


__all__ = ["SegmentStaticMember"]
