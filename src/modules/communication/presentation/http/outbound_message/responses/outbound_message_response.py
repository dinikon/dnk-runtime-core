from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class OutboundMessageResponseSchema(BaseModel):
    """HTTP response outbound message."""

    outbound_message_id: UUID
    tenant_id: UUID
    communication_request_id: UUID
    provider_connection_id: UUID
    channel_code: str
    recipient_identifier_type: str
    recipient_address: str
    recipient_snapshot: dict[str, Any]
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


__all__ = ["OutboundMessageResponseSchema"]
