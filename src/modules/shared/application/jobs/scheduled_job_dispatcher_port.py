from __future__ import annotations

from typing import Protocol

from src.modules.shared.domain.jobs import ScheduledJob


class ScheduledJobDispatcherPort(Protocol):
    """Application port that dispatches jobs to handlers by job type."""

    async def dispatch(self, job: ScheduledJob) -> None:
        """Dispatches a job to the matching handler."""
        ...


__all__ = ["ScheduledJobDispatcherPort"]
