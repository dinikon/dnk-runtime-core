from __future__ import annotations

from enum import StrEnum


class ScheduledJobStatus(StrEnum):
    """Lifecycle status for a shared scheduled job."""

    SCHEDULED = "scheduled"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELED = "canceled"

    def is_terminal(self) -> bool:
        """Returns True when no more processing is expected for the status."""
        return self in {
            ScheduledJobStatus.DONE,
            ScheduledJobStatus.FAILED,
            ScheduledJobStatus.CANCELED,
        }


__all__ = ["ScheduledJobStatus"]
