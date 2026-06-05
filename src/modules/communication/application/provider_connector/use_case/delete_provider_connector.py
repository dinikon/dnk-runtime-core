from typing import Protocol

from src.modules.communication.application.provider_connector.command import (
    DeleteProviderConnectorCommand,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnectorService,
)


class DeleteProviderConnectorUseCaseProtocol(Protocol):
    """Порт use case удаления provider connector."""

    async def __call__(self, command: DeleteProviderConnectorCommand) -> None:
        """Удаляет provider connector или архивирует его."""
        ...


class DeleteProviderConnectorUseCase:
    """Use case удаления provider connector."""

    def __init__(self, service: ProviderConnectorService) -> None:
        """Инициализирует use case доменным service."""
        self._service = service

    async def __call__(self, command: DeleteProviderConnectorCommand) -> None:
        """Выполняет удаление provider connector."""
        await self._service.delete_connector(
            tenant_id=command.tenant_id,
            provider_connector_id=command.provider_connector_id,
        )


__all__ = [
    "DeleteProviderConnectorUseCase",
    "DeleteProviderConnectorUseCaseProtocol",
]
