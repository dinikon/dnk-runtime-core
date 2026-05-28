from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version.value_object import (
    SegmentVersionIdVO,
    SegmentVersionStatusVO,
)


@dataclass(frozen=True, slots=True)
class SegmentVersion:
    """Versioned segment configuration."""

    segment_version_id: SegmentVersionIdVO
    segment_id: SegmentIdVO
    version_number: int
    status: SegmentVersionStatusVO
    config: dict[str, Any]
    config_checksum: str
    activated_at: datetime | None = None
    archived_at: datetime | None = None


__all__ = ["SegmentVersion"]
