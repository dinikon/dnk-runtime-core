from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProviderConnectionResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа provider connection."""

    provider_connection_id: UUID
    tenant_id: UUID
    provider_connector_id: UUID
    connection_name: str
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    has_secrets: bool
    status: str
    created_at: datetime
    updated_at: datetime


__all__ = ["ProviderConnectionResponseSchema"]
