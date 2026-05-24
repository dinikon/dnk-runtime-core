from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RecoverStuckScheduledJobsCommand:
    """Command for recovering expired running scheduled jobs."""

    limit: int = 100
    max_attempts: int = 5


__all__ = ["RecoverStuckScheduledJobsCommand"]
