from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class WorkflowEnvironmentVO:
    """Workflow state and secret variable definitions snapshot."""

    value: dict[str, Any] | list[Any]

    def __post_init__(self) -> None:
        if isinstance(self.value, Mapping):
            normalized = dict(self.value)
        elif isinstance(self.value, list):
            normalized = self.value
        else:
            raise InvalidWorkflowValueObjectError(
                "WorkflowEnvironmentVO value must be a mapping or list"
            )

        object.__setattr__(self, "value", deepcopy(normalized))


__all__ = ["WorkflowEnvironmentVO"]
