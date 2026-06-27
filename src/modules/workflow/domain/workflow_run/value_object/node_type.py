from dataclasses import dataclass

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class NodeTypeVO:
    """Workflow node adapter/action type."""

    value: str


__all__ = ["NodeTypeVO"]
