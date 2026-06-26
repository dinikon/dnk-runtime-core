from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class TriggeredFromVO:
    """Generic trigger source marker for workflow run."""

    value: str


__all__ = ["TriggeredFromVO"]
