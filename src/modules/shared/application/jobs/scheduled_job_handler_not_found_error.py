from __future__ import annotations


class ScheduledJobHandlerNotFoundError(RuntimeError):
    """Raised when a scheduled job type has no registered handler."""


__all__ = ["ScheduledJobHandlerNotFoundError"]
