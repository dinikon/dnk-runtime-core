from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ProviderConnectorDTO:
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


@dataclass(frozen=True, slots=True)
class ProviderMessageTypeDTO:
    provider_message_type_id: UUID
    provider_connector_id: UUID
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


@dataclass(frozen=True, slots=True)
class ProviderConnectionDTO:
    provider_connection_id: UUID
    tenant_id: UUID
    provider_connector_id: UUID
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    has_secrets: bool
    status: str
    created_at: datetime
    updated_at: datetime


__all__ = [
    "ProviderConnectionDTO",
    "ProviderConnectorDTO",
    "ProviderMessageTypeDTO",
]
