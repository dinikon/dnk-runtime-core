from __future__ import annotations

from pydantic import BaseModel

from src.modules.communication.presentation.http.delivery.responses.delivery_attempt_response import (
    DeliveryAttemptResponseSchema,
)


class ListDeliveryAttemptsResponseSchema(BaseModel):
    """HTTP response страницы delivery attempts."""

    items: list[DeliveryAttemptResponseSchema]


__all__ = ["ListDeliveryAttemptsResponseSchema"]
