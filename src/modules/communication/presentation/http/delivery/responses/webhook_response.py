from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class WebhookResponseSchema(BaseModel):
    """HTTP response обработки provider webhook."""

    accepted: bool
    matched: bool
    outbound_message_id: UUID | None
    internal_status: str | None


__all__ = ["WebhookResponseSchema"]
