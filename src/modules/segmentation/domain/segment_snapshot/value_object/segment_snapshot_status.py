from enum import StrEnum


class SegmentSnapshotStatusVO(StrEnum):
    """Segment snapshot status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


__all__ = ["SegmentSnapshotStatusVO"]
