from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateProviderConnectionRequestSchema(BaseModel):
    """Pydantic-схема тела запроса создания provider connection."""

    provider_connector_id: UUID
    connection_name: str
    channel_code: str
    config: dict[str, Any] = Field(default_factory=dict)
    secrets: dict[str, Any] = Field(default_factory=dict)
    secret_ref: str | None = None


__all__ = ["CreateProviderConnectionRequestSchema"]
