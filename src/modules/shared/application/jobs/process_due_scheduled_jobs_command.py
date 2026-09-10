from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessDueScheduledJobsCommand:
    """Command for one due scheduled jobs processing batch."""

    limit: int = 100
    max_attempts: int = 5
    lock_ttl_seconds: int = 300


__all__ = ["ProcessDueScheduledJobsCommand"]
