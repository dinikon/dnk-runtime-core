from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DeliveryEventDTO:
    """DTO delivery event для application boundary."""

    delivery_event_id: UUID
    tenant_id: UUID
    outbound_message_id: UUID | None
    provider_connection_id: UUID | None
    external_message_id: str | None
    external_status: str | None
    internal_status: str
    event_type: str
    event_at: datetime | None
    raw_payload: dict[str, Any]
    created_at: datetime


__all__ = ["DeliveryEventDTO"]
