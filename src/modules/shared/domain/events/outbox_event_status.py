from __future__ import annotations

from enum import StrEnum


class OutboxEventStatus(StrEnum):
    """Lifecycle status for persisted integration outbox events."""

    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


__all__ = ["OutboxEventStatus"]
