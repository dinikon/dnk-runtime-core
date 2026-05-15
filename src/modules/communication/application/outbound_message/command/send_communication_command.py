from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.modules.communication.domain.message_template import MessageTemplateIdVO
from src.modules.communication.domain.outbound_message import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class SendCommunicationCommand:
    """Команда постановки outbound communication send."""

    tenant_id: EntityIdVO
    initiator_type: str
    message_class: str
    channel_code: str
    recipient_address: str
    communication_request_id: CommunicationRequestIdVO | None = None
    outbound_message_id: OutboundMessageIdVO | None = None
    template_code: str | None = None
    template_id: MessageTemplateIdVO | None = None
    initiator_ref_id: str | None = None
    correlation_id: EntityIdVO | None = None
    idempotency_key: str | None = None
    contact_id: EntityIdVO | None = None
    recipient_snapshot: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100


__all__ = ["SendCommunicationCommand"]
