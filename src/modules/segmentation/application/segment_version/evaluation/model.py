from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.modules.segmentation.application.segment_version.evaluation.error import (
    SegmentVersionEvaluationError,
)


@dataclass(slots=True, frozen=True)
class ContactAudienceItemDTO:
    """Evaluated Contact audience item."""

    contact_id: UUID


@dataclass(slots=True, frozen=True)
class SegmentVersionEvaluationOptions:
    """Controls final evaluation pagination and per-query safety cap."""

    limit: int | None = None
    offset: int = 0
    max_items: int | None = None

    def __post_init__(self) -> None:
        if self.limit is not None and self.limit < 0:
            raise SegmentVersionEvaluationError("Evaluation limit must be >= 0.")
        if self.offset < 0:
            raise SegmentVersionEvaluationError("Evaluation offset must be >= 0.")
        if self.max_items is not None and self.max_items < 0:
            raise SegmentVersionEvaluationError("Evaluation max_items must be >= 0.")


@dataclass(slots=True, frozen=True)
class SegmentVersionEvaluationResult:
    """Contact audience evaluation result."""

    contact_ids: tuple[UUID, ...]
    count: int


__all__ = [
    "ContactAudienceItemDTO",
    "SegmentVersionEvaluationOptions",
    "SegmentVersionEvaluationResult",
]
