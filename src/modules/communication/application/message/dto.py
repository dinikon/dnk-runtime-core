from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SendCommunicationResultDTO:
    communication_request_id: UUID
    outbound_message_id: UUID
    status: str
    internal_status: str
    idempotent: bool


@dataclass(frozen=True, slots=True)
class OutboundMessageDTO:
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


@dataclass(frozen=True, slots=True)
class ProcessQueuedResultDTO:
    processed: int
    succeeded: int
    failed: int


@dataclass(frozen=True, slots=True)
class ProcessOutboundMessageResultDTO:
    outbound_message_id: UUID
    processed: bool
    succeeded: bool
    skipped: bool
    status: str
    error_message: str | None = None


__all__ = [
    "OutboundMessageDTO",
    "ProcessOutboundMessageResultDTO",
    "ProcessQueuedResultDTO",
    "SendCommunicationResultDTO",
]
