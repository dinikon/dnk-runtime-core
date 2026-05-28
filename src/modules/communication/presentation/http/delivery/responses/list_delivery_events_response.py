from __future__ import annotations

from pydantic import BaseModel

from src.modules.communication.presentation.http.delivery.responses.delivery_event_response import (
    DeliveryEventResponseSchema,
)


class ListDeliveryEventsResponseSchema(BaseModel):
    """HTTP response страницы delivery events."""

    items: list[DeliveryEventResponseSchema]


__all__ = ["ListDeliveryEventsResponseSchema"]
