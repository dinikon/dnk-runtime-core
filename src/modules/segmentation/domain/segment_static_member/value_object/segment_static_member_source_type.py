from enum import StrEnum


class SegmentStaticMemberSourceTypeVO(StrEnum):
    """Static member source type."""

    MANUAL = "manual"
    IMPORT = "import"
    API = "api"


__all__ = ["SegmentStaticMemberSourceTypeVO"]
