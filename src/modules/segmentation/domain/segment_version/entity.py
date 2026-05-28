from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Mapping

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_version.error import (
    InvalidSegmentVersionError,
    SegmentVersionTransitionError,
)
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

    def __post_init__(self) -> None:
        if not isinstance(self.segment_version_id, SegmentVersionIdVO):
            object.__setattr__(
                self,
                "segment_version_id",
                SegmentVersionIdVO.from_value(self.segment_version_id),
            )
        if not isinstance(self.segment_id, SegmentIdVO):
            object.__setattr__(
                self,
                "segment_id",
                SegmentIdVO.from_value(self.segment_id),
            )
        if self.version_number < 1:
            raise InvalidSegmentVersionError("Segment version number must be >= 1.")
        object.__setattr__(self, "status", SegmentVersionStatusVO(self.status))
        if not isinstance(self.config, Mapping):
            raise InvalidSegmentVersionError(
                "Segment version config must be a mapping."
            )
        object.__setattr__(self, "config", deepcopy(dict(self.config)))
        if (
            not isinstance(self.config_checksum, str)
            or not self.config_checksum.strip()
        ):
            raise InvalidSegmentVersionError(
                "Segment version config checksum must not be empty."
            )
        object.__setattr__(self, "config_checksum", self.config_checksum.strip())

    def activate(self, *, now: datetime) -> "SegmentVersion":
        """Activates a draft version."""
        if self.status != SegmentVersionStatusVO.DRAFT:
            raise SegmentVersionTransitionError(
                "Only draft segment version can be activated."
            )
        return replace(
            self,
            status=SegmentVersionStatusVO.ACTIVE,
            activated_at=now,
        )

    def archive(self, *, now: datetime) -> "SegmentVersion":
        """Archives version idempotently."""
        if self.status == SegmentVersionStatusVO.ARCHIVED:
            return self
        return replace(
            self,
            status=SegmentVersionStatusVO.ARCHIVED,
            archived_at=now,
        )


__all__ = ["SegmentVersion"]
