from __future__ import annotations

from pydantic import BaseModel

from src.modules.communication.presentation.http.outbound_message.responses.outbound_message_response import (
    OutboundMessageResponseSchema,
)


class ListOutboundMessagesResponseSchema(BaseModel):
    """HTTP response страницы outbound messages."""

    items: list[OutboundMessageResponseSchema]


__all__ = ["ListOutboundMessagesResponseSchema"]
