from __future__ import annotations

from typing import Protocol

from src.modules.shared.domain.jobs import ScheduledJob


class ScheduledJobHandlerPort(Protocol):
    """Application port implemented by concrete business job handlers."""

    async def handle(self, job: ScheduledJob) -> None:
        """Runs the concrete job logic."""
        ...


__all__ = ["ScheduledJobHandlerPort"]
