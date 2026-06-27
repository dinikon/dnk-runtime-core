from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class WorkflowErrorVO:
    """Workflow run or node error text snapshot."""

    value: str


__all__ = ["WorkflowErrorVO"]
