from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class WorkflowIconVO:
    """Workflow application icon identifier."""

    value: str


__all__ = ["WorkflowIconVO"]
