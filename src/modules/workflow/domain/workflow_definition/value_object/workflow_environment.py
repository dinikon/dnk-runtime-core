from __future__ import annotations

from enum import StrEnum

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


class WorkflowEnvironmentVO(StrEnum):
    """Workflow execution environment marker."""

    value: str


__all__ = ["WorkflowEnvironmentVO"]
