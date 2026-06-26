from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


@dataclass(frozen=True, slots=True)
class WorkflowPayloadVO:
    """Generic workflow execution payload snapshot."""

    value: dict[str, Any]


__all__ = ["WorkflowPayloadVO"]
