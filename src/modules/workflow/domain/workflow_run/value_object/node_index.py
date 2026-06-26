from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class NodeIndexVO:
    """Zero-based index of node execution inside a workflow run."""

    value: int


__all__ = ["NodeIndexVO"]
