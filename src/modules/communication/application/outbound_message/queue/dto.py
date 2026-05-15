from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublishQueuedResultDTO:
    scanned: int
    published: int
    failed: int


@dataclass(frozen=True, slots=True)
class RecoverStuckResultDTO:
    recovered: int


@dataclass(frozen=True, slots=True)
class OutboundMessageJob:
    tenant_id: UUID
    outbound_message_id: UUID
    published_at: datetime
    source: str

    def to_payload(self) -> dict[str, str]:
        return {
            "tenant_id": str(self.tenant_id),
            "outbound_message_id": str(self.outbound_message_id),
            "published_at": self.published_at.isoformat(),
            "source": self.source,
        }


__all__ = [
    "OutboundMessageJob",
    "PublishQueuedResultDTO",
    "RecoverStuckResultDTO",
]
