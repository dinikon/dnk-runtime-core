from __future__ import annotations

from pydantic import BaseModel


class ListMessageDeliveryEventsRequestSchema(BaseModel):
    """HTTP query params для events одного outbound message."""

    limit: int = 100
    offset: int = 0


__all__ = ["ListMessageDeliveryEventsRequestSchema"]
