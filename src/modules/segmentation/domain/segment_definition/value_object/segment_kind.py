from enum import StrEnum


class SegmentKindVO(StrEnum):
    """Segment kind."""

    STATIC = "static"
    DYNAMIC = "dynamic"


__all__ = ["SegmentKindVO"]
