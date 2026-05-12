from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.communication.domain.message_template.value_object import (
    MessageTemplateIdVO,
    TemplateVersionIdVO,
)
from src.modules.communication.domain.outbound_message.value_object import (
    CommunicationRequestIdVO,
    OutboundMessageIdVO,
)
from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class CommunicationRequest:
    communication_request_id: CommunicationRequestIdVO
    tenant_id: EntityIdVO
    initiator_type: str
    initiator_ref_id: str | None
    correlation_id: EntityIdVO | None
    idempotency_key: str | None
    message_class: str
    channel_code: str
    template_id: MessageTemplateIdVO
    template_version_id: TemplateVersionIdVO
    contact_id: EntityIdVO | None
    recipient_address: str
    recipient_snapshot: dict[str, Any]
    variables: dict[str, Any]
    scheduled_at: datetime | None
    priority: int
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class OutboundMessage:
    outbound_message_id: OutboundMessageIdVO
    tenant_id: EntityIdVO
    communication_request_id: CommunicationRequestIdVO
    provider_connection_id: ProviderConnectionIdVO
    channel_code: str
    message_class: str
    priority: int
    contact_id: EntityIdVO | None
    recipient_address: str
    rendered_payload: dict[str, Any]
    provider_request_payload: dict[str, Any]
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    error_code: str | None
    error_message: str | None
    queued_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    failed_at: datetime | None
    processing_token: EntityIdVO | None
    processing_started_at: datetime | None
    processing_deadline_at: datetime | None
    next_attempt_at: datetime | None
    queue_published_at: datetime | None
    queue_publish_count: int
    created_at: datetime
    updated_at: datetime


__all__ = [
    "CommunicationRequest",
    "OutboundMessage",
]
