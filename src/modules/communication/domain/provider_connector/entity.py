from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
    ProviderMessageTypeIdVO,
)


@dataclass(slots=True)
class ProviderConnector:
    provider_connector_id: ProviderConnectorIdVO
    provider_code: str
    provider_name: str
    version: str
    connector_type: str
    yaml_spec: dict[str, Any]
    yaml_checksum: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ProviderMessageType:
    provider_message_type_id: ProviderMessageTypeIdVO
    provider_connector_id: ProviderConnectorIdVO
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool


__all__ = [
    "ProviderConnector",
    "ProviderMessageType",
]
