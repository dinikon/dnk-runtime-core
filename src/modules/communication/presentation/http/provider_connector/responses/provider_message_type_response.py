from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProviderMessageTypeResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа provider message type."""

    provider_message_type_id: UUID
    provider_connector_id: UUID
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


__all__ = ["ProviderMessageTypeResponseSchema"]
