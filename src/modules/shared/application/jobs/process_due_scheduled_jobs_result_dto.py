from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessDueScheduledJobsResultDTO:
    """Result of one due scheduled jobs processing batch."""

    scanned: int
    processed: int
    done: int
    failed: int
    retried: int


__all__ = ["ProcessDueScheduledJobsResultDTO"]
