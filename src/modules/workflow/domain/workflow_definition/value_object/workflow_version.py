from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowVersionVO:
    """Workflow version label."""

    value: str


__all__ = ["WorkflowVersionVO"]
