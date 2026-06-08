from src.modules.shared import DomainError


class SegmentDefinitionError(DomainError):
    """Base segment definition domain error."""


class SegmentDefinitionNotFoundError(SegmentDefinitionError):
    """Raised when segment definition is missing."""

    def __init__(self, segment_id: str) -> None:
        super().__init__(f"Segment definition {segment_id} not found.")


class InvalidSegmentDefinitionNameError(SegmentDefinitionError):
    """Raised when segment definition name is blank."""

    def __init__(self) -> None:
        super().__init__("Segment definition name must not be empty.")


class SegmentDefinitionArchivedError(SegmentDefinitionError):
    """Raised when archived segment is mutated."""

    def __init__(self, segment_id: str) -> None:
        super().__init__(f"Archived segment {segment_id} cannot be changed.")


class SegmentDefinitionKindChangeError(SegmentDefinitionError):
    """Raised when code tries to change immutable segment kind."""

    def __init__(self, segment_id: str) -> None:
        super().__init__(f"Segment {segment_id} kind cannot be changed.")


__all__ = [
    "InvalidSegmentDefinitionNameError",
    "SegmentDefinitionArchivedError",
    "SegmentDefinitionError",
    "SegmentDefinitionKindChangeError",
    "SegmentDefinitionNotFoundError",
]
