from src.modules.shared.domain.errors import DomainError


class SegmentDefinitionError(DomainError):
    """Base segment definition domain error."""


class SegmentDefinitionNotFoundError(SegmentDefinitionError):
    """Raised when segment definition is missing."""

    def __init__(self, segment_id: str) -> None:
        super().__init__(f"Segment definition {segment_id} not found.")


__all__ = [
    "SegmentDefinitionError",
    "SegmentDefinitionNotFoundError",
]
