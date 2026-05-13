from typing import Protocol

from src.modules.communication.application.provider_connection.dto import (
    ProviderConnectionDTO,
)
from src.modules.communication.application.provider_connection.query import (
    ProviderConnectionQueryRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class ListProviderConnectionsUseCaseProtocol(Protocol):
    """Порт use case списка provider connections."""

    async def __call__(self, tenant_id: EntityIdVO) -> list[ProviderConnectionDTO]:
        """Возвращает список provider connections tenant."""
        ...


class ListProviderConnectionsUseCase:
    """Use case списка provider connections через query repository."""

    def __init__(self, repository: ProviderConnectionQueryRepositoryProtocol) -> None:
        """Инициализирует use case query repository подключений."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> list[ProviderConnectionDTO]:
        """Возвращает DTO provider connections tenant."""
        return await self._repository.list_connections(tenant_id=tenant_id)


__all__ = [
    "ListProviderConnectionsUseCase",
    "ListProviderConnectionsUseCaseProtocol",
]
