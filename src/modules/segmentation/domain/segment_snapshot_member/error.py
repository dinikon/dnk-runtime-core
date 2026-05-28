from src.modules.shared.domain.errors import DomainError


class SegmentSnapshotMemberError(DomainError):
    """Base segment snapshot member domain error."""


class InvalidSegmentSnapshotMemberError(SegmentSnapshotMemberError):
    """Raised when segment snapshot member data is invalid."""


__all__ = [
    "InvalidSegmentSnapshotMemberError",
    "SegmentSnapshotMemberError",
]
