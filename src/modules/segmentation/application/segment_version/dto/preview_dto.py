from dataclasses import dataclass
from uuid import UUID

from src.modules.segmentation.application.segment_static_member.dto import (
    ContactSummaryDTO,
)


@dataclass(slots=True, frozen=True)
class SegmentPreviewDTO:
    """Read-only Contact segment preview result."""

    contact_ids: tuple[UUID, ...]
    contacts: tuple[ContactSummaryDTO, ...]
    limit: int
    offset: int
    count: int
    total: int | None
    has_more: bool


__all__ = ["SegmentPreviewDTO"]
