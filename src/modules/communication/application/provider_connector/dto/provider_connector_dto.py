from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderConnectorDTO:
    """DTO provider connector для application boundary."""

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


__all__ = ["ProviderConnectorDTO"]
