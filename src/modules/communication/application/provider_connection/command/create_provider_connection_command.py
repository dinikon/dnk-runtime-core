from dataclasses import dataclass, field
from typing import Any

from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.shared import EntityIdVO


@dataclass(slots=True, frozen=True)
class CreateProviderConnectionCommand:
    """Команда application-слоя на создание provider connection tenant."""

    tenant_id: EntityIdVO
    provider_connection_id: ProviderConnectionIdVO
    provider_connector_id: ProviderConnectorIdVO
    connection_name: str
    channel_code: str
    config: dict[str, Any] = field(default_factory=dict)
    secrets: dict[str, Any] = field(default_factory=dict)
    secret_ref: str | None = None


__all__ = ["CreateProviderConnectionCommand"]
