from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ListDeliveryEventsRequestSchema(BaseModel):
    """HTTP query params для delivery events."""

    outbound_message_id: UUID | None = None
    external_message_id: str | None = None
    internal_status: str | None = None
    event_type: str | None = None
    limit: int = 100
    offset: int = 0


__all__ = [
    "ListDeliveryEventsRequestSchema",
]
