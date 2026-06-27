from __future__ import annotations

from typing import Any, Mapping

from src.modules.communication.domain.provider_connector.enum import ConnectorStatus
from src.modules.communication.domain.provider_connector.entity import ProviderConnector
from src.modules.communication.domain.provider_connector.error import (
    ProviderConnectorArchivedError,
    ProviderConnectorNotFoundError,
)
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
        provider_code = ProviderConnectorCodeVO(str(spec["provider_code"]))
        version = ProviderConnectorVersionVO(str(spec["version"]))
        existing = await self._repository.load_connector_by_code_version(
            tenant_id=tenant_id,
            provider_code=provider_code,
            version=version,
        )
        if existing is not None and existing.status == ConnectorStatus.ARCHIVED.value:
            raise ProviderConnectorArchivedError()

        provider_connector_id = (
            provider_connector_id
            if existing is None
            else existing.provider_connector_id
        )
        status = ConnectorStatus.ACTIVE.value if existing is None else existing.status
        connector_candidate = ProviderConnector.create(
            provider_connector_id=provider_connector_id,
            provider_code=provider_code.value,
            provider_name=str(spec["provider_name"]),
            version=version.value,
            connector_type=str(spec["connector_type"]),
            yaml_spec=dict(spec),
            yaml_checksum=checksum,
            status=status,
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

    async def change_connector_status(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        status: ConnectorStatus,
    ) -> ProviderConnector:
        """Меняет статус provider connector по lifecycle-правилам."""
        connector = await self._repository.load_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()
        connector.change_status(status=status, now=self._clock.now())
        return await self._repository.upsert_connector(
            tenant_id=tenant_id,
            provider_connector_id=connector.provider_connector_id,
            provider_code=ProviderConnectorCodeVO(connector.provider_code),
            provider_name=ProviderConnectorNameVO(connector.provider_name),
            version=ProviderConnectorVersionVO(connector.version),
            connector_type=connector.connector_type,
            yaml_spec=connector.yaml_spec,
            yaml_checksum=connector.yaml_checksum,
            status=connector.status,
        )

    async def delete_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> None:
        """Удаляет connector физически или архивирует при наличии связей."""
        connector = await self._repository.load_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()
        connector.ensure_deletable()
        has_usage = await self._repository.has_usage(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        if has_usage:
            connector.archive(now=self._clock.now())
            await self._repository.upsert_connector(
                tenant_id=tenant_id,
                provider_connector_id=connector.provider_connector_id,
                provider_code=ProviderConnectorCodeVO(connector.provider_code),
                provider_name=ProviderConnectorNameVO(connector.provider_name),
                version=ProviderConnectorVersionVO(connector.version),
                connector_type=connector.connector_type,
                yaml_spec=connector.yaml_spec,
                yaml_checksum=connector.yaml_checksum,
                status=connector.status,
            )
            return
        await self._repository.delete_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )


__all__ = ["ProviderConnectorService"]
