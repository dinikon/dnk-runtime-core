from typing import Protocol

from src.modules.communication.application.provider_connection.command import (
    DeleteProviderConnectionCommand,
)
from src.modules.communication.domain.provider_connection import (
    ProviderConnectionService,
)


class DeleteProviderConnectionUseCaseProtocol(Protocol):
    """Порт use case удаления provider connection."""

    async def __call__(self, command: DeleteProviderConnectionCommand) -> None:
        """Удаляет provider connection или архивирует его."""
        ...


class DeleteProviderConnectionUseCase:
    """Use case удаления provider connection."""

    def __init__(self, service: ProviderConnectionService) -> None:
        """Инициализирует use case доменным service."""
        self._service = service

    async def __call__(self, command: DeleteProviderConnectionCommand) -> None:
        """Выполняет удаление provider connection."""
        await self._service.delete_connection(
            tenant_id=command.tenant_id,
            provider_connection_id=command.provider_connection_id,
        )


__all__ = [
    "DeleteProviderConnectionUseCase",
    "DeleteProviderConnectionUseCaseProtocol",
]
