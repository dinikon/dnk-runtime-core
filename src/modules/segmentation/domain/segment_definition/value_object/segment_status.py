from enum import StrEnum


class SegmentStatusVO(StrEnum):
    """Segment definition status."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


__all__ = ["SegmentStatusVO"]
