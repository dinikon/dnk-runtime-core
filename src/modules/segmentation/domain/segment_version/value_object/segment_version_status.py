from enum import StrEnum


class SegmentVersionStatusVO(StrEnum):
    """Segment version status."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


__all__ = ["SegmentVersionStatusVO"]
