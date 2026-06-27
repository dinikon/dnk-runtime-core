from typing import Protocol

from src.modules.communication.application.provider_connection.command import (
    UpdateProviderConnectionStatusCommand,
)
from src.modules.communication.application.provider_connection.dto import (
    ProviderConnectionDTO,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionEntity,
    ProviderConnectionService,
    ProviderConnectionStatusVO,
)


class UpdateProviderConnectionStatusUseCaseProtocol(Protocol):
    """Порт use case смены статуса provider connection."""

    async def __call__(
        self,
        command: UpdateProviderConnectionStatusCommand,
    ) -> ProviderConnectionDTO:
        """Меняет статус provider connection и возвращает DTO."""
        ...


class UpdateProviderConnectionStatusUseCase:
    """Use case смены статуса provider connection."""

    def __init__(self, service: ProviderConnectionService) -> None:
        """Инициализирует use case доменным service."""
        self._service = service

    async def __call__(
        self,
        command: UpdateProviderConnectionStatusCommand,
    ) -> ProviderConnectionDTO:
        """Выполняет смену статуса provider connection."""
        connection = await self._service.change_connection_status(
            tenant_id=command.tenant_id,
            provider_connection_id=command.provider_connection_id,
            status=ProviderConnectionStatusVO(command.status),
        )
        return self._to_dto(connection)

    @staticmethod
    def _to_dto(connection: ProviderConnectionEntity) -> ProviderConnectionDTO:
        """Мапит ProviderConnectionEntity в ProviderConnectionDTO."""
        return ProviderConnectionDTO(
            provider_connection_id=connection.provider_connection_id.uuid,
            tenant_id=connection.tenant_id.uuid,
            provider_connector_id=connection.provider_connector_id.uuid,
            connection_name=connection.connection_name.value,
            channel_code=connection.channel_code,
            config=dict(connection.config or {}),
            secret_ref=connection.secret_ref,
            has_secrets=bool(connection.secrets_b64),
            status=connection.status.value,
            created_at=connection.created_at,
            updated_at=connection.updated_at,
        )


__all__ = [
    "UpdateProviderConnectionStatusUseCase",
    "UpdateProviderConnectionStatusUseCaseProtocol",
]
