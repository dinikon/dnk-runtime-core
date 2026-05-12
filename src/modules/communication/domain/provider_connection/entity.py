from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(slots=True)
class ProviderConnection:
    provider_connection_id: ProviderConnectionIdVO
    tenant_id: EntityIdVO
    provider_connector_id: ProviderConnectorIdVO
    connection_code: str
    connection_name: str
    channel_code: str
    config: dict[str, Any]
    secret_ref: str | None
    secrets_b64: str | None
    status: str
    created_at: datetime
    updated_at: datetime


__all__ = ["ProviderConnection"]
