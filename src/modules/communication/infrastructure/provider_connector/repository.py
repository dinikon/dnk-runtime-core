from __future__ import annotations

from typing import Any

from src.modules.communication.application.provider_connector.query import (
    ProviderConnectorQueryRepositoryProtocol,
)
from src.modules.communication.domain.provider_connector import (
    ConnectorStatus,
    ProviderChannelCodeVO,
    ProviderConnector,
    ProviderConnectorCodeVO,
    ProviderConnectorIdVO,
    ProviderConnectorNameVO,
    ProviderConnectorNotFoundError,
    ProviderConnectorRepositoryProtocol,
    ProviderConnectorVersionVO,
    ProviderMessageType,
    ProviderMessageTypeCodeVO,
    ProviderMessageTypeNameVO,
)
from src.modules.communication.infrastructure.provider_connector.row_mapper import (
    provider_connector_dto,
    provider_connector_entity,
    provider_message_type_dto,
    provider_message_type_entity,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _CONNECTION,
    _CONNECTOR,
    _MESSAGE_TYPE,
    _TEMPLATE,
)
from src.modules.runtime_data.application.models import PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.runtime_data.application.query.typed_filter_builder import (
    RuntimeTypedFilterBuilder,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class ProviderConnectorRuntimeRepository(
    ProviderConnectorRepositoryProtocol,
    ProviderConnectorQueryRepositoryProtocol,
):
    """Runtime repository provider connector aggregate."""

    _OBJECT_NAME = _CONNECTOR
    _MESSAGE_TYPE_OBJECT_NAME = _MESSAGE_TYPE

    def __init__(
        self,
        *,
        runtime_object_resolver: RuntimeObjectResolverProtocol,
        runtime_command_gateway: RuntimeCommandGateway,
        runtime_query_gateway: RuntimeQueryGateway,
    ) -> None:
        """Инициализирует repository resolver-ом descriptor и runtime gateways."""
        self._runtime_object_resolver = runtime_object_resolver
        self._runtime_command_gateway = runtime_command_gateway
        self._runtime_query_gateway = runtime_query_gateway
        self._filter_builder = RuntimeTypedFilterBuilder()

    async def load_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> ProviderConnector | None:
        """Загружает provider connector entity из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=provider_connector_id.uuid,
        )
        if row is None:
            return None
        return provider_connector_entity(row)

    async def load_connector_by_code_version(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_code: ProviderConnectorCodeVO,
        version: ProviderConnectorVersionVO,
    ) -> ProviderConnector | None:
        """Загружает provider connector entity по tenant-local code/version."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="provider_code",
                    op="eq",
                    value=provider_code.value,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="version",
                    op="eq",
                    value=version.value,
                ),
            ),
            sorting=(SortSpec("created_at", "asc"),),
            page=PageSpec(limit=1, offset=0),
        )
        if not rows:
            return None
        return provider_connector_entity(rows[0])

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
        """Создает или обновляет runtime-строку provider connector."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        existing = await self.load_connector_by_code_version(
            tenant_id=tenant_id,
            provider_code=provider_code,
            version=version,
        )
        payload = {
            "provider_code": provider_code.value,
            "provider_name": provider_name.value,
            "version": version.value,
            "connector_type": connector_type,
            "yaml_spec": dict(yaml_spec),
            "yaml_checksum": yaml_checksum,
            "status": status,
        }
        if existing is not None:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=existing.provider_connector_id.uuid,
                patch=payload,
            )
            if row is None:
                raise ProviderConnectorNotFoundError()
        else:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": provider_connector_id.uuid,
                    **payload,
                },
            )
        return provider_connector_entity(row)

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
        """Создает или обновляет runtime-строку provider message type."""
        descriptor = await self._resolve_descriptor(
            tenant_id,
            self._MESSAGE_TYPE_OBJECT_NAME,
        )
        existing = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="provider_connector_id",
                    op="eq",
                    value=provider_connector_id.uuid,
                ),
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="message_type_code",
                    op="eq",
                    value=message_type_code.value,
                ),
            ),
            sorting=(SortSpec("created_at", "asc"),),
            page=PageSpec(limit=1, offset=0),
        )
        payload = {
            "provider_connector_id": provider_connector_id.uuid,
            "message_type_code": message_type_code.value,
            "channel_code": channel_code.value,
            "name": name.value,
            "field_schema": dict(field_schema),
            "ui_schema": dict(ui_schema),
            "is_active": is_active,
        }
        if existing:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=existing[0]["id"],
                patch=payload,
            )
            if row is None:
                raise ProviderConnectorNotFoundError()
        else:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload=payload,
            )
        return provider_message_type_entity(row)

    async def list_connectors(
        self,
        *,
        tenant_id: EntityIdVO,
    ):
        """Возвращает DTO provider connectors tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="status",
                    op="neq",
                    value=ConnectorStatus.ARCHIVED.value,
                ),
            ),
            sorting=(SortSpec("provider_code"), SortSpec("version")),
        )
        return [provider_connector_dto(row) for row in rows]

    async def list_message_types(
        self,
        *,
        tenant_id: EntityIdVO,
    ):
        """Возвращает DTO provider message types tenant."""
        connectors = await self.list_connectors(tenant_id=tenant_id)
        connector_ids = [connector.provider_connector_id for connector in connectors]
        if not connector_ids:
            return []
        descriptor = await self._resolve_descriptor(
            tenant_id,
            self._MESSAGE_TYPE_OBJECT_NAME,
        )
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                self._filter_builder.condition(
                    descriptor=descriptor,
                    field="provider_connector_id",
                    op="in",
                    value=connector_ids,
                ),
            ),
            sorting=(SortSpec("channel_code"), SortSpec("message_type_code")),
        )
        return [provider_message_type_dto(row) for row in rows]

    async def has_usage(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> bool:
        """Проверяет provider connections/templates по connector id."""
        for object_name in (_CONNECTION, _TEMPLATE):
            descriptor = await self._resolve_descriptor(tenant_id, object_name)
            rows = await self._runtime_query_gateway.list(
                descriptor=descriptor,
                filters=(
                    self._filter_builder.condition(
                        descriptor=descriptor,
                        field="provider_connector_id",
                        op="eq",
                        value=provider_connector_id.uuid,
                    ),
                ),
                page=PageSpec(limit=1, offset=0),
            )
            if rows:
                return True
        return False

    async def delete_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> None:
        """Физически удаляет provider connector runtime row."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        deleted = await self._runtime_command_gateway.delete(
            descriptor=descriptor,
            object_id=provider_connector_id.uuid,
        )
        if not deleted:
            raise ProviderConnectorNotFoundError()

    async def _resolve_descriptor(self, tenant_id: EntityIdVO, object_name: str):
        """Получает runtime descriptor communication-объекта для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )


__all__ = ["ProviderConnectorRuntimeRepository"]
