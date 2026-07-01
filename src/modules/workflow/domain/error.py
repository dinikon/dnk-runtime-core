from src.modules.shared import DomainError


class WorkflowError(DomainError):
    """Base domain error for workflow module."""


class WorkflowValidationError(WorkflowError):
    """Raised when workflow domain data is invalid."""


class WorkflowApplicationNotFoundError(WorkflowError):
    """Raised when workflow application is not found."""

    def __init__(self, workflow_id: str):
        super().__init__(f"Workflow application {workflow_id} not found")


class InvalidWorkflowValueObjectError(WorkflowValidationError):
    """Raised when workflow value object data is invalid."""


__all__ = [
    "InvalidWorkflowValueObjectError",
    "WorkflowApplicationNotFoundError",
    "WorkflowError",
    "WorkflowValidationError",
]
