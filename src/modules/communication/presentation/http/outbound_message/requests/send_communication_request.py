from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SendCommunicationRequestSchema(BaseModel):
    """HTTP schema команды отправки communication message."""

    initiator_type: str
    message_class: str
    channel_code: str
    recipient_address: str
    template_code: str | None = None
    template_id: UUID | None = None
    initiator_ref_id: str | None = None
    correlation_id: UUID | None = None
    idempotency_key: str | None = None
    contact_id: UUID | None = None
    recipient_snapshot: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100


__all__ = ["SendCommunicationRequestSchema"]
