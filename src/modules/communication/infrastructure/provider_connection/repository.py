from __future__ import annotations

from src.modules.communication.application.provider_connection.query import (
    ProviderConnectionQueryRepositoryProtocol,
)
from src.modules.communication.application.provider_connection.dto import (
    ProviderConnectionDTO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionIdVO,
    ProviderConnectionNotFoundError,
    ProviderConnectionProviderLookupProtocol,
    ProviderConnectionRepositoryProtocol,
    ProviderConnectionStatusVO,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderConnectorIdVO,
)
from src.modules.communication.infrastructure.provider_connection.row_mapper import (
    provider_connection_dto,
    provider_connection_entity,
    provider_connector_entity,
)
from src.modules.communication.infrastructure.runtime_object_names import (
    _CONNECTION,
    _CONNECTOR,
)
from src.modules.runtime_data import FilterSpec, PageSpec, SortSpec
from src.modules.runtime_data.application.ports import (
    RuntimeCommandGateway,
    RuntimeQueryGateway,
)
from src.modules.schema_registry.runtime import RuntimeObjectResolverProtocol
from src.modules.shared import EntityIdVO


class ProviderConnectionRuntimeRepository(
    ProviderConnectionRepositoryProtocol,
    ProviderConnectionProviderLookupProtocol,
    ProviderConnectionQueryRepositoryProtocol,
):
    """Runtime repository provider connection aggregate."""

    _OBJECT_NAME = _CONNECTION

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

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connection_id: ProviderConnectionIdVO,
    ) -> ProviderConnectionEntity | None:
        """Загружает provider connection entity из runtime-таблицы tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=provider_connection_id.uuid,
        )
        if row is None:
            return None
        return provider_connection_entity(tenant_id=tenant_id, row=row)

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        connection: ProviderConnectionEntity,
    ) -> ProviderConnectionEntity:
        """Создает или обновляет runtime-строку connection и возвращает entity."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        existing = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=connection.provider_connection_id.uuid,
        )
        payload = {
            "provider_connector_id": connection.provider_connector_id.uuid,
            "connection_code": connection.connection_code.value,
            "connection_name": connection.connection_name.value,
            "channel_code": connection.channel_code,
            "config": connection.config,
            "secret_ref": connection.secret_ref,
            "secrets_b64": connection.secrets_b64,
            "status": connection.status.value,
        }
        if existing is None:
            row = await self._runtime_command_gateway.insert(
                descriptor=descriptor,
                payload={
                    "id": connection.provider_connection_id.uuid,
                    **payload,
                },
            )
        else:
            row = await self._runtime_command_gateway.update(
                descriptor=descriptor,
                object_id=connection.provider_connection_id.uuid,
                patch=payload,
            )
            if row is None:
                raise ProviderConnectionNotFoundError()
        return provider_connection_entity(tenant_id=tenant_id, row=row)

    async def find_active(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        channel_code: str,
    ) -> ProviderConnectionEntity | None:
        """Ищет active provider connection по connector и channel."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            filters=(
                FilterSpec("provider_connector_id", "eq", provider_connector_id.uuid),
                FilterSpec("channel_code", "eq", channel_code),
                FilterSpec("status", "eq", ProviderConnectionStatusVO.ACTIVE.value),
            ),
            sorting=(SortSpec("created_at"),),
            page=PageSpec(limit=1, offset=0),
        )
        if not rows:
            return None
        return provider_connection_entity(tenant_id=tenant_id, row=rows[0])

    async def find_active_connection(
        self,
        *,
        tenant_id,
        provider_connector_id,
        channel_code: str,
    ) -> ProviderConnectionEntity | None:
        """Совместимый lookup для outbound send repository protocol."""
        tenant_vo = (
            tenant_id
            if type(tenant_id) is EntityIdVO
            else EntityIdVO.from_value(tenant_id)
        )
        connector_vo = (
            provider_connector_id
            if type(provider_connector_id) is ProviderConnectorIdVO
            else ProviderConnectorIdVO.from_value(provider_connector_id)
        )
        return await self.find_active(
            tenant_id=tenant_vo,
            provider_connector_id=connector_vo,
            channel_code=channel_code,
        )

    async def load_provider_connector(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connector_id: ProviderConnectorIdVO,
    ) -> ProviderConnector | None:
        """Загружает provider connector entity для domain checks."""
        descriptor = await self._resolve_descriptor(tenant_id, _CONNECTOR)
        row = await self._runtime_query_gateway.get_by_id(
            descriptor=descriptor,
            object_id=provider_connector_id.uuid,
        )
        if row is None:
            return None
        return provider_connector_entity(row)

    async def list_connections(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[ProviderConnectionDTO]:
        """Возвращает DTO provider connections tenant."""
        descriptor = await self._resolve_descriptor(tenant_id, self._OBJECT_NAME)
        rows = await self._runtime_query_gateway.list(
            descriptor=descriptor,
            sorting=(SortSpec("connection_code"),),
        )
        return [
            provider_connection_dto(
                tenant_id=tenant_id,
                row=row,
            )
            for row in rows
        ]

    async def _resolve_descriptor(self, tenant_id: EntityIdVO, object_name: str):
        """Получает runtime descriptor communication-объекта для tenant."""
        return await self._runtime_object_resolver.resolve(
            tenant_id=tenant_id,
            object_name=object_name,
        )


__all__ = ["ProviderConnectionRuntimeRepository"]
