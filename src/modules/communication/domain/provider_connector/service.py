from __future__ import annotations

from typing import Any, Mapping

from src.modules.communication.domain.provider_connector.enum import ConnectorStatus
from src.modules.communication.domain.provider_connector.entity import ProviderConnector
from src.modules.communication.domain.provider_connector.repository import (
    ProviderConnectorRepositoryProtocol,
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
from src.modules.shared.domain.time import ClockPort


class ProviderConnectorService:
    """Доменный сервис регистрации provider connector из YAML spec."""

    def __init__(
        self,
        *,
        repository: ProviderConnectorRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис repository и clock-портом."""
        self._repository = repository
        self._clock = clock

    async def register_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        spec: Mapping[str, Any],
        checksum: str,
    ) -> ProviderConnector:
        """Регистрирует connector и его message types в tenant runtime."""
        connector_candidate = ProviderConnector.create(
            provider_connector_id=provider_connector_id,
            provider_code=str(spec["provider_code"]),
            provider_name=str(spec["provider_name"]),
            version=str(spec["version"]),
            connector_type=str(spec["connector_type"]),
            yaml_spec=dict(spec),
            yaml_checksum=checksum,
            status=ConnectorStatus.ACTIVE.value,
            now=self._clock.now(),
        )
        connector = await self._repository.upsert_connector(
            tenant_id=tenant_id,
            provider_connector_id=connector_candidate.provider_connector_id,
            provider_code=ProviderConnectorCodeVO(connector_candidate.provider_code),
            provider_name=ProviderConnectorNameVO(connector_candidate.provider_name),
            version=ProviderConnectorVersionVO(connector_candidate.version),
            connector_type=connector_candidate.connector_type,
            yaml_spec=connector_candidate.yaml_spec,
            yaml_checksum=connector_candidate.yaml_checksum,
            status=connector_candidate.status,
        )
        for message_type in spec["message_types"]:
            await self._repository.upsert_message_type(
                tenant_id=tenant_id,
                provider_connector_id=connector.provider_connector_id,
                message_type_code=ProviderMessageTypeCodeVO(str(message_type["code"])),
                channel_code=ProviderChannelCodeVO(str(message_type["channel"])),
                name=ProviderMessageTypeNameVO(str(message_type["name"])),
                field_schema=dict(message_type["field_schema"]),
                ui_schema=dict(message_type.get("ui_schema") or {}),
                is_active=True,
            )
        return connector


__all__ = ["ProviderConnectorService"]
