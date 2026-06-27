from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class NodeIdVO:
    """Workflow graph node identifier."""

    value: str


__all__ = ["NodeIdVO"]
