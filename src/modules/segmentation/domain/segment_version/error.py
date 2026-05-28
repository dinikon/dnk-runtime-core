from src.modules.shared.domain.errors import DomainError


class SegmentVersionError(DomainError):
    """Base segment version domain error."""


class SegmentVersionNotFoundError(SegmentVersionError):
    """Raised when segment version is missing."""

    def __init__(self, segment_version_id: str) -> None:
        super().__init__(f"Segment version {segment_version_id} not found.")


class InvalidSegmentVersionError(SegmentVersionError):
    """Raised when segment version data is invalid."""


class SegmentVersionTransitionError(SegmentVersionError):
    """Raised when segment version status transition is invalid."""


__all__ = [
    "InvalidSegmentVersionError",
    "SegmentVersionError",
    "SegmentVersionNotFoundError",
    "SegmentVersionTransitionError",
]
