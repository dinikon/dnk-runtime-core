from src.modules.shared.domain.errors import DomainError


class SegmentStaticMemberError(DomainError):
    """Base static member domain error."""


class SegmentStaticMemberContactNotFoundError(SegmentStaticMemberError):
    """Raised when a Contact member does not exist."""

    def __init__(self, contact_id: str) -> None:
        super().__init__(f"Contact {contact_id} not found.")


class SegmentStaticMemberArchivedSegmentError(SegmentStaticMemberError):
    """Raised when archived segment is mutated."""

    def __init__(self, segment_id: str) -> None:
        super().__init__(f"Archived segment {segment_id} cannot be changed.")


class SegmentStaticMemberNonStaticSegmentError(SegmentStaticMemberError):
    """Raised when static members are added to a non-static segment."""

    def __init__(self, segment_id: str) -> None:
        super().__init__(
            f"Segment {segment_id} must be static to manage static members."
        )


__all__ = [
    "SegmentStaticMemberArchivedSegmentError",
    "SegmentStaticMemberContactNotFoundError",
    "SegmentStaticMemberError",
    "SegmentStaticMemberNonStaticSegmentError",
]
