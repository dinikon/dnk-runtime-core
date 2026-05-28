from __future__ import annotations

from pydantic import BaseModel


class ListMessageDeliveryAttemptsRequestSchema(BaseModel):
    """HTTP query params для attempts одного outbound message."""

    limit: int = 100
    offset: int = 0


__all__ = ["ListMessageDeliveryAttemptsRequestSchema"]
