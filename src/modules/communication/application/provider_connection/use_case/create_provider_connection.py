from typing import Protocol

from src.modules.communication.application.provider_connection.command import (
    CreateProviderConnectionCommand,
)
from src.modules.communication.application.provider_connection.dto import (
    ProviderConnectionDTO,
)
from src.modules.communication.application.services import SecretCodec
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionService,
)


class CreateProviderConnectionUseCaseProtocol(Protocol):
    """Порт доменного сервиса создания provider connection."""

    async def __call__(
        self, command: CreateProviderConnectionCommand
    ) -> ProviderConnectionDTO:
        """Создает provider connection через domain layer."""
        ...


class CreateProviderConnectionUseCase:
    """Use case создания provider connection через доменный сервис."""

    def __init__(
        self,
        service: ProviderConnectionService,
        secret_codec: SecretCodec,
    ) -> None:
        """Инициализирует use case service и codec-ом секретов."""
        self._service = service
        self._secret_codec = secret_codec

    async def __call__(
        self,
        command: CreateProviderConnectionCommand,
    ) -> ProviderConnectionDTO:
        """Выполняет команду создания connection и мапит entity в DTO."""
        connection = await self._service.create_connection(
            tenant_id=command.tenant_id,
            provider_connection_id=command.provider_connection_id,
            provider_connector_id=command.provider_connector_id,
            connection_code=command.connection_code,
            connection_name=command.connection_name,
            channel_code=command.channel_code,
            config=command.config,
            secrets=command.secrets,
            secret_ref=command.secret_ref,
            secrets_b64=self._secret_codec.encode(command.secrets),
        )
        return self._to_dto(connection)

    @staticmethod
    def _to_dto(connection: ProviderConnectionEntity) -> ProviderConnectionDTO:
        """Мапит ProviderConnectionEntity в ProviderConnectionDTO."""
        return ProviderConnectionDTO(
            provider_connection_id=connection.provider_connection_id.uuid,
            tenant_id=connection.tenant_id.uuid,
            provider_connector_id=connection.provider_connector_id.uuid,
            connection_code=connection.connection_code.value,
            connection_name=connection.connection_name.value,
            channel_code=connection.channel_code,
            config=dict(connection.config or {}),
            secret_ref=connection.secret_ref,
            has_secrets=bool(connection.secrets_b64),
            status=connection.status.value,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


__all__ = ["CreateProviderConnectionUseCase", "CreateProviderConnectionUseCaseProtocol"]
