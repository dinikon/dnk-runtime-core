from src.modules.shared.domain.errors import DomainError


class SegmentSnapshotError(DomainError):
    """Base segment snapshot domain error."""


class InvalidSegmentSnapshotError(SegmentSnapshotError):
    """Raised when segment snapshot data is invalid."""


class SegmentSnapshotNotFoundError(SegmentSnapshotError):
    """Raised when segment snapshot is not found."""

    def __init__(self, segment_snapshot_id: str) -> None:
        super().__init__(f"Segment snapshot {segment_snapshot_id} not found.")


class SegmentSnapshotTransitionError(SegmentSnapshotError):
    """Raised when snapshot status transition is invalid."""


class SegmentSnapshotImmutableError(SegmentSnapshotError):
    """Raised when completed snapshot is mutated."""


__all__ = [
    "InvalidSegmentSnapshotError",
    "SegmentSnapshotError",
    "SegmentSnapshotImmutableError",
    "SegmentSnapshotNotFoundError",
    "SegmentSnapshotTransitionError",
]
