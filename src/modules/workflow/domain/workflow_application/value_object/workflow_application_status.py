from __future__ import annotations

from enum import StrEnum

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


class WorkflowApplicationStatusVO(StrEnum):
    """Lifecycle status of workflow application."""

    NORMAL = "NORMAL"


__all__ = ["WorkflowApplicationStatusVO"]
