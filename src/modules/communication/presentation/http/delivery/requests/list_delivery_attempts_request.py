from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class ListDeliveryAttemptsRequestSchema(BaseModel):
    """HTTP query params для delivery attempts."""

    outbound_message_id: UUID | None = None
    status: str | None = None
    limit: int = 100
    offset: int = 0


__all__ = [
    "ListDeliveryAttemptsRequestSchema",
]
