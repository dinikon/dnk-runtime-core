from __future__ import annotations

from collections.abc import Mapping

from src.modules.shared.application.jobs.scheduled_job_handler_not_found_error import (
    ScheduledJobHandlerNotFoundError,
)
from src.modules.shared.application.jobs.scheduled_job_handler_port import (
    ScheduledJobHandlerPort,
)
from src.modules.shared.domain.jobs import ScheduledJob


class InMemoryScheduledJobDispatcher:
    """In-process registry dispatcher for future scheduled job workers."""

    def __init__(
        self,
        handlers: Mapping[str, ScheduledJobHandlerPort] | None = None,
    ) -> None:
        self._handlers = dict(handlers or {})

    async def dispatch(self, job: ScheduledJob) -> None:
        """Dispatches a job to a handler registered for its job type."""
        handler = self._handlers.get(job.job_type)
        if handler is None:
            raise ScheduledJobHandlerNotFoundError(
                f"No scheduled job handler registered for job_type={job.job_type!r}."
            )
        await handler.handle(job)


__all__ = ["InMemoryScheduledJobDispatcher"]
