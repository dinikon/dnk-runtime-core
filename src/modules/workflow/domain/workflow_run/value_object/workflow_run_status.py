from __future__ import annotations

from enum import StrEnum

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


class WorkflowRunStatusVO(StrEnum):
    """Lifecycle status of workflow run."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


__all__ = ["WorkflowRunStatusVO"]
