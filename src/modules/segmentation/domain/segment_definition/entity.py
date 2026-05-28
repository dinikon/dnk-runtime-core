from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.modules.segmentation.domain.segment_definition.value_object import (
    SegmentIdVO,
    SegmentKindVO,
    SegmentStatusVO,
)


@dataclass(frozen=True, slots=True)
class SegmentDefinition:
    """Contact-only segment definition."""

    segment_id: SegmentIdVO
    name: str
    segment_kind: SegmentKindVO
    status: SegmentStatusVO
    description: str | None = None
    archived_at: datetime | None = None


__all__ = ["SegmentDefinition"]
