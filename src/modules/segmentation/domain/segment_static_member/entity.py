from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Self

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

    @classmethod
    def create(
        cls,
        *,
        segment_static_member_id: SegmentStaticMemberIdVO,
        segment_id: SegmentIdVO,
        contact_id: EntityIdVO,
        source_type: SegmentStaticMemberSourceTypeVO,
        metadata: Mapping[str, Any] | None = None,
    ) -> Self:
        """Creates static member from already prepared value objects."""
        normalized_metadata = cls._copy_metadata(metadata)
        return cls(
            segment_static_member_id=segment_static_member_id,
            segment_id=segment_id,
            contact_id=contact_id,
            source_type=source_type,
            metadata=normalized_metadata,
        )

    @staticmethod
    def _copy_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if metadata is None:
            return None
        if not isinstance(metadata, Mapping):
            raise SegmentStaticMemberError("Static member metadata must be a mapping.")
        return deepcopy(dict(metadata))


__all__ = ["SegmentStaticMember"]
