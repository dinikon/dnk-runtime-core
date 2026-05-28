from dataclasses import dataclass
from typing import Any, Mapping

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class CreateSegmentVersionCommand:
    """Command for creating draft segment version."""

    tenant_id: EntityIdVO
    segment_id: SegmentIdVO
    config: Mapping[str, Any]


__all__ = ["CreateSegmentVersionCommand"]
