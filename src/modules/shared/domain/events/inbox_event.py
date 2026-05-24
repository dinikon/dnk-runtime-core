from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class InboxEvent:
    """Persisted consumer idempotency record."""

    id: UUID
    tenant_id: UUID
    source: str
    message_id: str
    event_type: str
    consumed_at: datetime | None
    status: str
    error: str | None


__all__ = ["InboxEvent"]
