from src.modules.shared.domain.errors import DomainError


class SegmentVersionDslError(DomainError):
    """Base error for segment version DSL config failures."""

    def __init__(self, message: str, *, path: str) -> None:
        self.path = path
        super().__init__(f"{path}: {message}")


class SegmentVersionDslParseError(SegmentVersionDslError):
    """Raised when DSL config cannot be parsed."""


class SegmentVersionDslValidationError(SegmentVersionDslError):
    """Raised when parsed DSL config violates semantic rules."""


class SegmentVersionDslInvalidRootObjectError(SegmentVersionDslValidationError):
    """Raised when root object is not contact."""


class SegmentVersionDslRuleLimitError(SegmentVersionDslValidationError):
    """Raised when DSL rule count exceeds configured limits."""


class SegmentVersionDslInvalidRuleError(SegmentVersionDslValidationError):
    """Raised when a DSL rule is malformed or references invalid metadata."""


class SegmentVersionDslInvalidRelationPathError(SegmentVersionDslValidationError):
    """Raised when a relation path cannot be resolved."""


class SegmentVersionDslInvalidContactMappingError(SegmentVersionDslValidationError):
    """Raised when a rule cannot map records back to contacts."""


class SegmentVersionDslInvalidInheritedSegmentError(SegmentVersionDslValidationError):
    """Raised when inherited segment references are invalid."""


__all__ = [
    "SegmentVersionDslError",
    "SegmentVersionDslInvalidContactMappingError",
    "SegmentVersionDslInvalidInheritedSegmentError",
    "SegmentVersionDslInvalidRelationPathError",
    "SegmentVersionDslInvalidRootObjectError",
    "SegmentVersionDslInvalidRuleError",
    "SegmentVersionDslParseError",
    "SegmentVersionDslRuleLimitError",
    "SegmentVersionDslValidationError",
]
