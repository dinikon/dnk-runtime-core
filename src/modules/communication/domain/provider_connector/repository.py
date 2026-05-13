from __future__ import annotations

from typing import Any, Protocol

from src.modules.communication.domain.provider_connector.entity import (
    ProviderConnector,
    ProviderMessageType,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderChannelCodeVO,
    ProviderConnectorCodeVO,
    ProviderConnectorIdVO,
    ProviderConnectorNameVO,
    ProviderConnectorVersionVO,
    ProviderMessageTypeCodeVO,
    ProviderMessageTypeNameVO,
)
from src.modules.shared import EntityIdVO


class ProviderConnectorRepositoryProtocol(Protocol):
    """Порт командного хранения provider connector aggregate."""

    async def upsert_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        provider_code: ProviderConnectorCodeVO,
        provider_name: ProviderConnectorNameVO,
        version: ProviderConnectorVersionVO,
        connector_type: str,
        yaml_spec: dict[str, Any],
        yaml_checksum: str,
        status: str,
    ) -> ProviderConnector:
        """Создает или обновляет provider connector tenant."""
        ...

    async def upsert_message_type(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        message_type_code: ProviderMessageTypeCodeVO,
        channel_code: ProviderChannelCodeVO,
        name: ProviderMessageTypeNameVO,
        field_schema: dict[str, Any],
        ui_schema: dict[str, Any],
        is_active: bool,
    ) -> ProviderMessageType:
        """Создает или обновляет provider message type tenant."""
        ...


__all__ = ["ProviderConnectorRepositoryProtocol"]
