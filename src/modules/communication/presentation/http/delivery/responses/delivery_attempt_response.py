from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DeliveryAttemptResponseSchema(BaseModel):
    """HTTP response delivery attempt."""

    delivery_attempt_id: UUID
    tenant_id: UUID
    outbound_message_id: UUID
    provider_connection_id: UUID
    attempt_no: int
    status: str
    request_payload: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    http_status_code: int | None
    external_message_id: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


__all__ = ["DeliveryAttemptResponseSchema"]
