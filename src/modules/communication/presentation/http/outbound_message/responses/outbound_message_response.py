from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.modules.communication.application.outbound_message import OutboundMessageDTO


class OutboundMessageResponseSchema(BaseModel):
    """HTTP response outbound message."""

    outbound_message_id: UUID
    tenant_id: UUID
    communication_request_id: UUID
    provider_connection_id: UUID
    channel_code: str
    contact_id: UUID | None
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
    created_at: datetime
    updated_at: datetime


def outbound_message_response(
    item: OutboundMessageDTO,
) -> OutboundMessageResponseSchema:
    """Мапит application DTO в HTTP response schema."""
    return OutboundMessageResponseSchema(
        outbound_message_id=item.outbound_message_id,
        tenant_id=item.tenant_id,
        communication_request_id=item.communication_request_id,
        provider_connection_id=item.provider_connection_id,
        channel_code=item.channel_code,
        contact_id=item.contact_id,
        recipient_address=item.recipient_address,
        rendered_payload=dict(item.rendered_payload),
        provider_request_payload=dict(item.provider_request_payload),
        external_message_id=item.external_message_id,
        external_status=item.external_status,
        internal_status=item.internal_status,
        error_code=item.error_code,
        error_message=item.error_message,
        queued_at=item.queued_at,
        sent_at=item.sent_at,
        delivered_at=item.delivered_at,
        failed_at=item.failed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


__all__ = [
    "OutboundMessageResponseSchema",
    "outbound_message_response",
]
