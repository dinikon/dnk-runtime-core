from __future__ import annotations

from enum import StrEnum

from src.modules.workflow.domain.error import InvalidWorkflowValueObjectError


class NodeExecutionStatusVO(StrEnum):
    """Lifecycle status of node execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


__all__ = ["NodeExecutionStatusVO"]
