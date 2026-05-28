from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from src.modules.segmentation.domain.segment_definition.error import (
    InvalidSegmentDefinitionNameError,
    SegmentDefinitionArchivedError,
    SegmentDefinitionKindChangeError,
)
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

    def __post_init__(self) -> None:
        if not isinstance(self.segment_id, SegmentIdVO):
            object.__setattr__(
                self,
                "segment_id",
                SegmentIdVO.from_value(self.segment_id),
            )
        normalized_name = self._normalize_name(self.name)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "segment_kind", SegmentKindVO(self.segment_kind))
        object.__setattr__(self, "status", SegmentStatusVO(self.status))
        if self.description is not None:
            object.__setattr__(self, "description", str(self.description))

    def update(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        description_provided: bool = False,
        segment_kind: SegmentKindVO | None = None,
    ) -> "SegmentDefinition":
        """Returns updated segment definition or raises on immutable changes."""
        if self.status == SegmentStatusVO.ARCHIVED:
            raise SegmentDefinitionArchivedError(str(self.segment_id))
        if (
            segment_kind is not None
            and SegmentKindVO(segment_kind) != self.segment_kind
        ):
            raise SegmentDefinitionKindChangeError(str(self.segment_id))
        return replace(
            self,
            name=self.name if name is None else self._normalize_name(name),
            description=(description if description_provided else self.description),
        )

    def archive(self, *, now: datetime) -> "SegmentDefinition":
        """Archives segment idempotently."""
        if self.status == SegmentStatusVO.ARCHIVED:
            return self
        return replace(
            self,
            status=SegmentStatusVO.ARCHIVED,
            archived_at=now,
        )

    @staticmethod
    def _normalize_name(value: str) -> str:
        if not isinstance(value, str):
            raise InvalidSegmentDefinitionNameError()
        normalized = value.strip()
        if not normalized:
            raise InvalidSegmentDefinitionNameError()
        return normalized


__all__ = ["SegmentDefinition"]
