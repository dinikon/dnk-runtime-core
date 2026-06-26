from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class WorkflowIconBackgroundVO:
    """Workflow application icon background value."""

    value: str


__all__ = ["WorkflowIconBackgroundVO"]
