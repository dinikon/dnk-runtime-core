from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SendCommunicationCommand:
    tenant_id: UUID
    initiator_type: str
    message_class: str
    channel_code: str
    recipient_address: str
    template_code: str | None = None
    template_id: UUID | None = None
    initiator_ref_id: str | None = None
    correlation_id: UUID | None = None
    idempotency_key: str | None = None
    contact_id: UUID | None = None
    recipient_snapshot: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100


@dataclass(frozen=True, slots=True)
class ProcessQueuedMessagesCommand:
    tenant_id: UUID
    limit: int = 100


@dataclass(frozen=True, slots=True)
class ProcessOutboundMessageByIdCommand:
    tenant_id: UUID
    outbound_message_id: UUID


__all__ = [
    "ProcessOutboundMessageByIdCommand",
    "ProcessQueuedMessagesCommand",
    "SendCommunicationCommand",
]
