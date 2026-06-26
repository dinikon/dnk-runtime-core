from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class ElapsedTimeVO:
    """Elapsed execution time in seconds."""

    value: float


__all__ = ["ElapsedTimeVO"]
