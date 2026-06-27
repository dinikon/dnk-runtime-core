from __future__ import annotations

from enum import StrEnum


class WorkflowKindVO(StrEnum):
    """Low-level workflow orchestration kind."""

    STANDARD = "STANDARD"

    BROADCAST = "BROADCAST"
    CAMPAIGN = "CAMPAIGN"


__all__ = ["WorkflowKindVO"]
