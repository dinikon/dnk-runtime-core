from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublishQueuedOutboundMessagesCommand:
    tenant_id: UUID
    limit: int = 100
    source: str = "republisher"


@dataclass(frozen=True, slots=True)
class RecoverStuckOutboundMessagesCommand:
    tenant_id: UUID
    older_than_seconds: int = 300
    limit: int = 100


__all__ = [
    "PublishQueuedOutboundMessagesCommand",
    "RecoverStuckOutboundMessagesCommand",
]
