from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class TotalStepsVO:
    """Total planned node execution count."""

    value: int


__all__ = ["TotalStepsVO"]
