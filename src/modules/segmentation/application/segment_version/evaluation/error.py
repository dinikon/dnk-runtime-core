from src.modules.shared import DomainError


class SegmentVersionEvaluationError(DomainError):
    """Base error for segment version evaluation failures."""


class SegmentVersionEvaluationFilterError(SegmentVersionEvaluationError):
    """Raised when a validated DSL filter cannot be converted for runtime_data."""


class SegmentVersionEvaluationInvalidMappingError(SegmentVersionEvaluationError):
    """Raised when runtime rows cannot be mapped to Contact ids."""


class SegmentVersionEvaluationUnsupportedRelationPathError(
    SegmentVersionEvaluationError
):
    """Raised when evaluator cannot execute a relation path."""


class SegmentVersionEvaluationInheritanceCycleError(SegmentVersionEvaluationError):
    """Raised when inherited segment evaluation detects a cycle."""


class SegmentVersionEvaluationDepthExceededError(SegmentVersionEvaluationError):
    """Raised when inherited segment nesting exceeds supported depth."""


class SegmentVersionActiveVersionNotFoundError(SegmentVersionEvaluationError):
    """Raised when dynamic inherited segment has no active version."""

    def __init__(self, segment_id: str) -> None:
        super().__init__(f"Active segment version for segment {segment_id} not found.")


__all__ = [
    "SegmentVersionActiveVersionNotFoundError",
    "SegmentVersionEvaluationDepthExceededError",
    "SegmentVersionEvaluationError",
    "SegmentVersionEvaluationFilterError",
    "SegmentVersionEvaluationInheritanceCycleError",
    "SegmentVersionEvaluationInvalidMappingError",
    "SegmentVersionEvaluationUnsupportedRelationPathError",
]
