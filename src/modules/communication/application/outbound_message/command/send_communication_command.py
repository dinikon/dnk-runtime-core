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
    initiator_ref_id: str
    correlation_id: EntityIdVO
    idempotency_key: str
    channel_code: str
    template_id: MessageTemplateIdVO
    recipient_identifier_type: str
    recipient_address: str
    recipient_snapshot: dict[str, Any]
    communication_request_id: CommunicationRequestIdVO | None = None
    outbound_message_id: OutboundMessageIdVO | None = None
    message_class: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100


__all__ = ["SendCommunicationCommand"]
