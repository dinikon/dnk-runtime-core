from __future__ import annotations

from typing import Any, Mapping, Protocol

from src.modules.communication.domain.error import CommunicationValidationError
from src.modules.communication.domain.provider_connection.entity import (
    ProviderConnectionEntity,
)
from src.modules.communication.domain.provider_connection.repository import (
    ProviderConnectionProviderLookupProtocol,
    ProviderConnectionRepositoryProtocol,
)
from src.modules.communication.domain.provider_connection.value_object import (
    ProviderConnectionIdVO,
)
from src.modules.communication.domain.provider_connector.error import (
    ProviderConnectorNotFoundError,
)
from src.modules.communication.domain.provider_connector.value_object import (
    ProviderConnectorIdVO,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.domain.time import ClockPort


class ProviderConnectionSchemaValidatorProtocol(Protocol):
    """Порт валидации config/secrets provider connection."""

    def validate_provider_config(
        self,
        payload: dict[str, Any],
        schema: Mapping[str, Any] | None,
    ) -> None:
        """Проверяет config по JSON Schema provider connector."""
        ...

    def validate_provider_secrets(
        self,
        payload: dict[str, Any],
        schema: Mapping[str, Any] | None,
    ) -> None:
        """Проверяет secrets по JSON Schema provider connector."""
        ...


class ProviderConnectionService:
    """Доменный сервис сценариев provider connection aggregate."""

    def __init__(
        self,
        *,
        command_repository: ProviderConnectionRepositoryProtocol,
        provider_lookup: ProviderConnectionProviderLookupProtocol,
        schema_validator: ProviderConnectionSchemaValidatorProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует сервис repository, provider lookup и clock-портом."""
        self._command_repository = command_repository
        self._provider_lookup = provider_lookup
        self._schema_validator = schema_validator
        self._clock = clock

    async def create_connection(
        self,
        *,
        tenant_id: EntityIdVO,
        provider_connection_id: ProviderConnectionIdVO,
        provider_connector_id: ProviderConnectorIdVO,
        connection_code: str,
        connection_name: str,
        channel_code: str,
        config: dict[str, Any],
        secrets: dict[str, Any],
        secret_ref: str | None,
        secrets_b64: str | None,
    ) -> ProviderConnectionEntity:
        """Создает provider connection, проверяя connector, channel и schemas."""
        connector = await self._provider_lookup.load_provider_connector(
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
        )
        if connector is None:
            raise ProviderConnectorNotFoundError()

        spec = connector.yaml_spec
        if channel_code not in set(spec.get("channels") or []):
            raise CommunicationValidationError(
                "Provider connector does not support requested channel."
            )

        self._schema_validator.validate_provider_config(
            config,
            spec.get("config_schema"),
        )
        self._schema_validator.validate_provider_secrets(
            secrets,
            spec.get("secrets_schema"),
        )

        connection = ProviderConnectionEntity.create(
            provider_connection_id=provider_connection_id,
            tenant_id=tenant_id,
            provider_connector_id=provider_connector_id,
            connection_code=connection_code,
            connection_name=connection_name,
            channel_code=channel_code,
            config=config,
            secret_ref=secret_ref,
            secrets_b64=secrets_b64,
            now=self._clock.now(),
        )
        return await self._command_repository.save(
            tenant_id=tenant_id,
            connection=connection,
        )


__all__ = [
    "ProviderConnectionSchemaValidatorProtocol",
    "ProviderConnectionService",
]
