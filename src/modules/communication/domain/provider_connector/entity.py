from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from src.modules.communication.domain.provider_connector.enum import (
    ConnectorStatus,
    ConnectorType,
)
from src.modules.communication.domain.provider_connector.error import (
    InvalidProviderConnectorStatusError,
    InvalidProviderConnectorTypeError,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderChannelCodeVO,
    ProviderConnectorCodeVO,
    ProviderConnectorIdVO,
    ProviderConnectorNameVO,
    ProviderConnectorVersionVO,
    ProviderMessageTypeCodeVO,
    ProviderMessageTypeIdVO,
    ProviderMessageTypeNameVO,
)


@dataclass(slots=True)
class ProviderConnector:
    """Доменная сущность provider connector."""

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

    @classmethod
    def create(
        cls,
        *,
        provider_connector_id: ProviderConnectorIdVO,
        provider_code: str,
        provider_name: str,
        version: str,
        connector_type: str,
        yaml_spec: dict[str, Any],
        yaml_checksum: str,
        now: datetime,
        status: str = ConnectorStatus.ACTIVE.value,
    ) -> Self:
        """Создает provider connector с нормализованными доменными значениями."""
        try:
            connector_type_value = ConnectorType(connector_type).value
        except ValueError as exc:
            raise InvalidProviderConnectorTypeError() from exc
        try:
            status_value = ConnectorStatus(status).value
        except ValueError as exc:
            raise InvalidProviderConnectorStatusError() from exc
        return cls(
            provider_connector_id=provider_connector_id,
            provider_code=ProviderConnectorCodeVO(provider_code).value,
            provider_name=ProviderConnectorNameVO(provider_name).value,
            version=ProviderConnectorVersionVO(version).value,
            connector_type=connector_type_value,
            yaml_spec=dict(yaml_spec),
            yaml_checksum=yaml_checksum,
            status=status_value,
            created_at=now,
            updated_at=now,
        )


@dataclass(slots=True)
class ProviderMessageType:
    """Доменная сущность типа сообщения provider connector."""

    provider_message_type_id: ProviderMessageTypeIdVO
    provider_connector_id: ProviderConnectorIdVO
    message_type_code: str
    channel_code: str
    name: str
    field_schema: dict[str, Any]
    ui_schema: dict[str, Any]
    is_active: bool

    @classmethod
    def create(
        cls,
        *,
        provider_message_type_id: ProviderMessageTypeIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        message_type_code: str,
        channel_code: str,
        name: str,
        field_schema: dict[str, Any],
        ui_schema: dict[str, Any],
        is_active: bool = True,
    ) -> Self:
        """Создает provider message type с нормализованными значениями."""
        return cls(
            provider_message_type_id=provider_message_type_id,
            provider_connector_id=provider_connector_id,
            message_type_code=ProviderMessageTypeCodeVO(message_type_code).value,
            channel_code=ProviderChannelCodeVO(channel_code).value,
            name=ProviderMessageTypeNameVO(name).value,
            field_schema=dict(field_schema),
            ui_schema=dict(ui_schema),
            is_active=is_active,
        )


__all__ = [
    "ProviderConnector",
    "ProviderMessageType",
]
