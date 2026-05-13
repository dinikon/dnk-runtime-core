from __future__ import annotations

from src.modules.communication.application.provider_connector.command import (
    RegisterProviderConnectorCommand,
)
from src.modules.communication.application.provider_connector.dto import (
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
)
from src.modules.communication.application.provider_connector.ports import (
    ProviderConnectorRepositoryProtocol,
)
from src.modules.communication.application.services import (
    ProviderYamlLoader,
)


class RegisterProviderConnectorUseCase:
    """Imports provider YAML and extracts provider message types."""

    def __init__(
        self,
        repository: ProviderConnectorRepositoryProtocol,
        loader: ProviderYamlLoader,
    ) -> None:
        self._repository = repository
        self._loader = loader

    async def __call__(
        self,
        command: RegisterProviderConnectorCommand,
    ) -> ProviderConnectorDTO:
        parsed = self._loader.load(command.yaml_content)
        spec = parsed.spec
        connector = await self._repository.upsert_connector(
            tenant_id=command.tenant_id,
            provider_code=str(spec["provider_code"]),
            provider_name=str(spec["provider_name"]),
            version=str(spec["version"]),
            connector_type=str(spec["connector_type"]),
            yaml_spec=spec,
            yaml_checksum=parsed.checksum,
        )
        for message_type in spec["message_types"]:
            await self._repository.upsert_message_type(
                tenant_id=command.tenant_id,
                provider_connector_id=connector.provider_connector_id.uuid,
                message_type_code=str(message_type["code"]),
                channel_code=str(message_type["channel"]),
                name=str(message_type["name"]),
                field_schema=dict(message_type["field_schema"]),
                ui_schema=dict(message_type.get("ui_schema") or {}),
            )
        connector_spec = connector.yaml_spec or {}
        return ProviderConnectorDTO(
            provider_connector_id=connector.provider_connector_id.uuid,
            provider_code=connector.provider_code,
            provider_name=connector.provider_name,
            version=connector.version,
            connector_type=connector.connector_type,
            channels=list(connector_spec.get("channels") or []),
            config_schema=dict(connector_spec.get("config_schema") or {}),
            secrets_schema=dict(connector_spec.get("secrets_schema") or {}),
            status=connector.status,
            created_at=connector.created_at,
            updated_at=connector.updated_at,
        )


class ListProviderConnectorsUseCase:
    """Lists provider connectors and message types."""

    def __init__(self, repository: ProviderConnectorRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(
        self,
        tenant_id,
    ) -> tuple[list[ProviderConnectorDTO], list[ProviderMessageTypeDTO]]:
        connectors = []
        for connector in await self._repository.list_connectors(tenant_id):
            connector_spec = connector.yaml_spec or {}
            connectors.append(
                ProviderConnectorDTO(
                    provider_connector_id=connector.provider_connector_id.uuid,
                    provider_code=connector.provider_code,
                    provider_name=connector.provider_name,
                    version=connector.version,
                    connector_type=connector.connector_type,
                    channels=list(connector_spec.get("channels") or []),
                    config_schema=dict(connector_spec.get("config_schema") or {}),
                    secrets_schema=dict(connector_spec.get("secrets_schema") or {}),
                    status=connector.status,
                    created_at=connector.created_at,
                    updated_at=connector.updated_at,
                )
            )
        message_types = []
        for message_type in await self._repository.list_message_types(tenant_id):
            message_types.append(
                ProviderMessageTypeDTO(
                    provider_message_type_id=message_type.provider_message_type_id.uuid,
                    provider_connector_id=message_type.provider_connector_id.uuid,
                    message_type_code=message_type.message_type_code,
                    channel_code=message_type.channel_code,
                    name=message_type.name,
                    field_schema=dict(message_type.field_schema or {}),
                    ui_schema=dict(message_type.ui_schema or {}),
                    is_active=bool(message_type.is_active),
                )
            )
        return connectors, message_types


__all__ = [
    "ListProviderConnectorsUseCase",
    "RegisterProviderConnectorUseCase",
]
