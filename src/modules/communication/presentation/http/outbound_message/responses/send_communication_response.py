from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class SendCommunicationResponseSchema(BaseModel):
    """HTTP response результата постановки send request."""

    communication_request_id: UUID
    outbound_message_id: UUID
    status: str
    internal_status: str
    idempotent: bool


__all__ = ["SendCommunicationResponseSchema"]
