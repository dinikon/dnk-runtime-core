from src.modules.shared import DomainError


class WorkflowError(DomainError):
    """Base domain error for workflow module."""


class WorkflowValidationError(WorkflowError):
    """Raised when workflow domain data is invalid."""


class InvalidWorkflowValueObjectError(WorkflowValidationError):
    """Raised when workflow value object data is invalid."""


__all__ = [
    "InvalidWorkflowValueObjectError",
    "WorkflowError",
    "WorkflowValidationError",
]
