from __future__ import annotations

from src.modules.communication.application.provider_connection.command import (
    CreateProviderConnectionCommand,
)
from src.modules.communication.application.provider_connection.dto import (
    ProviderConnectionDTO,
)
from src.modules.communication.application.provider_connection.ports import (
    ProviderConnectionRepositoryProtocol,
)
from src.modules.communication.application.services import (
    JsonSchemaValidationService,
    SecretCodec,
)
from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorNotFoundError,
)


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
]
