from __future__ import annotations

from datetime import datetime, timedelta


class ScheduledJobRetryPolicy:
    """Linear retry backoff policy for scheduled jobs."""

    def __init__(self, retry_base_seconds: int) -> None:
        self._retry_base_seconds = retry_base_seconds

    def next_retry_at(self, *, now: datetime, attempts: int) -> datetime:
        """Returns next retry timestamp for the current attempt count."""
        return now + timedelta(seconds=self._retry_base_seconds * max(1, attempts))


__all__ = ["ScheduledJobRetryPolicy"]
