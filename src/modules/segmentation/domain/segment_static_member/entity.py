from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from src.modules.segmentation.domain.segment_definition import SegmentIdVO
from src.modules.segmentation.domain.segment_static_member.error import (
    SegmentStaticMemberError,
)
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

    def __post_init__(self) -> None:
        if not isinstance(self.segment_static_member_id, SegmentStaticMemberIdVO):
            object.__setattr__(
                self,
                "segment_static_member_id",
                SegmentStaticMemberIdVO.from_value(self.segment_static_member_id),
            )
        if not isinstance(self.segment_id, SegmentIdVO):
            object.__setattr__(
                self,
                "segment_id",
                SegmentIdVO.from_value(self.segment_id),
            )
        if not isinstance(self.contact_id, EntityIdVO):
            object.__setattr__(
                self,
                "contact_id",
                EntityIdVO.from_value(self.contact_id),
            )
        object.__setattr__(
            self,
            "source_type",
            SegmentStaticMemberSourceTypeVO(self.source_type),
        )
        if self.metadata is not None:
            if not isinstance(self.metadata, Mapping):
                raise SegmentStaticMemberError(
                    "Static member metadata must be a mapping."
                )
            object.__setattr__(self, "metadata", deepcopy(dict(self.metadata)))


__all__ = ["SegmentStaticMember"]
