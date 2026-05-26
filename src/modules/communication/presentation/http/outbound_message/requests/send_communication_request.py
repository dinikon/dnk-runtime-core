from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SendCommunicationRequestSchema(BaseModel):
    """HTTP schema команды отправки communication message."""

    model_config = ConfigDict(extra="forbid")

    initiator_type: str
    initiator_ref_id: str = Field(min_length=1)
    correlation_id: UUID
    idempotency_key: str = Field(min_length=1)
    channel_code: str
    template_id: UUID
    recipient_identifier_type: str = Field(min_length=1)
    recipient_address: str
    recipient_snapshot: dict[str, Any]
    message_class: str | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    scheduled_at: datetime | None = None
    priority: int = 100

    @field_validator(
        "initiator_type",
        "initiator_ref_id",
        "idempotency_key",
        "channel_code",
        "recipient_identifier_type",
        "recipient_address",
    )
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        """Reject blank required text fields at HTTP boundary."""
        if not value.strip():
            raise ValueError("Field must not be blank")
        return value


__all__ = ["SendCommunicationRequestSchema"]
