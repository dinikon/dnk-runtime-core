from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProviderConnectorResponseSchema(BaseModel):
    """Pydantic-схема HTTP-ответа provider connector."""

    provider_connector_id: UUID
    provider_code: str
    provider_name: str
    version: str
    connector_type: str
    channels: list[str]
    config_schema: dict[str, Any]
    secrets_schema: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime


__all__ = ["ProviderConnectorResponseSchema"]
