from src.modules.shared.domain.errors import DomainError


class SegmentSnapshotError(DomainError):
    """Base segment snapshot domain error."""


class InvalidSegmentSnapshotError(SegmentSnapshotError):
    """Raised when segment snapshot data is invalid."""


class SegmentSnapshotTransitionError(SegmentSnapshotError):
    """Raised when snapshot status transition is invalid."""


class SegmentSnapshotImmutableError(SegmentSnapshotError):
    """Raised when completed snapshot is mutated."""


__all__ = [
    "InvalidSegmentSnapshotError",
    "SegmentSnapshotError",
    "SegmentSnapshotImmutableError",
    "SegmentSnapshotTransitionError",
]
