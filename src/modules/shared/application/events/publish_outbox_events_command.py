from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublishOutboxEventsCommand:
    """Command for publishing due integration outbox events."""

    limit: int = 100
    max_attempts: int = 5


__all__ = ["PublishOutboxEventsCommand"]
