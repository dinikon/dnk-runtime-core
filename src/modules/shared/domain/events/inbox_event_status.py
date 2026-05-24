from __future__ import annotations

from enum import StrEnum


class InboxEventStatus(StrEnum):
    """Lifecycle status for inbox idempotency records."""

    RECEIVED = "received"
    CONSUMED = "consumed"
    FAILED = "failed"


__all__ = ["InboxEventStatus"]
