from __future__ import annotations

from src.modules.communication.application.provider.command import (
    CreateProviderConnectionCommand,
    RegisterProviderConnectorCommand,
)
from src.modules.communication.application.provider.dto import (
    ProviderConnectionDTO,
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
)
from src.modules.communication.application.provider.ports import (
    ProviderConnectionRepositoryProtocol,
    ProviderConnectorRepositoryProtocol,
)
from src.modules.communication.application.services import (
    JsonSchemaValidationService,
    ProviderYamlLoader,
    SecretCodec,
)
from src.modules.communication.domain import (
    CommunicationValidationError,
    ProviderConnectorNotFoundError,
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


class CreateProviderConnectionUseCase:
    """Creates tenant provider connections with write-only base64 secrets."""

    def __init__(
        self,
        repository: ProviderConnectionRepositoryProtocol,
        schema_validator: JsonSchemaValidationService,
        secret_codec: SecretCodec,
    ) -> None:
        self._repository = repository
        self._schema_validator = schema_validator
        self._secret_codec = secret_codec

    async def __call__(
        self,
        command: CreateProviderConnectionCommand,
    ) -> ProviderConnectionDTO:
        connector = await self._repository.get_connector(
            command.tenant_id,
            command.provider_connector_id,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()
        spec = connector.yaml_spec
        if command.channel_code not in set(spec.get("channels") or []):
            raise CommunicationValidationError(
                "Provider connector does not support requested channel."
            )
        self._schema_validator.validate(
            command.config, spec.get("config_schema"), "config"
        )
        self._schema_validator.validate(
            command.secrets,
            spec.get("secrets_schema"),
            "secrets",
        )
        connection = await self._repository.create_connection(
            tenant_id=command.tenant_id,
            provider_connector_id=command.provider_connector_id,
            connection_code=command.connection_code,
            connection_name=command.connection_name,
            channel_code=command.channel_code,
            config=command.config,
            secret_ref=command.secret_ref,
            secrets_b64=self._secret_codec.encode(command.secrets),
        )
        return ProviderConnectionDTO(
            provider_connection_id=connection.provider_connection_id.uuid,
            tenant_id=connection.tenant_id.uuid,
            provider_connector_id=connection.provider_connector_id.uuid,
            connection_code=connection.connection_code,
            connection_name=connection.connection_name,
            channel_code=connection.channel_code,
            config=dict(connection.config or {}),
            secret_ref=connection.secret_ref,
            has_secrets=bool(connection.secrets_b64),
            status=connection.status,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


class ListProviderConnectionsUseCase:
    """Lists tenant provider connections without exposing secrets."""

    def __init__(self, repository: ProviderConnectionRepositoryProtocol) -> None:
        self._repository = repository

    async def __call__(self, tenant_id) -> list[ProviderConnectionDTO]:
        items = []
        for connection in await self._repository.list_connections(tenant_id):
            items.append(
                ProviderConnectionDTO(
                    provider_connection_id=connection.provider_connection_id.uuid,
                    tenant_id=connection.tenant_id.uuid,
                    provider_connector_id=connection.provider_connector_id.uuid,
                    connection_code=connection.connection_code,
                    connection_name=connection.connection_name,
                    channel_code=connection.channel_code,
                    config=dict(connection.config or {}),
                    secret_ref=connection.secret_ref,
                    has_secrets=bool(connection.secrets_b64),
                    status=connection.status,
                    created_at=connection.created_at,
                    updated_at=connection.updated_at,
                )
            )
        return items


__all__ = [
    "CreateProviderConnectionUseCase",
    "ListProviderConnectionsUseCase",
    "ListProviderConnectorsUseCase",
    "RegisterProviderConnectorUseCase",
]
