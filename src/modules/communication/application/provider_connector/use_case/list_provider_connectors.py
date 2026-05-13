from typing import Protocol

from src.modules.communication.application.provider_connector.dto import (
    ProviderConnectorCatalogDTO,
)
from src.modules.communication.application.provider_connector.query import (
    ProviderConnectorQueryRepositoryProtocol,
)
from src.modules.shared import EntityIdVO


class ListProviderConnectorsUseCaseProtocol(Protocol):
    """Порт use case списка provider connectors."""

    async def __call__(self, tenant_id: EntityIdVO) -> ProviderConnectorCatalogDTO:
        """Возвращает каталог provider connectors tenant."""
        ...


class ListProviderConnectorsUseCase:
    """Use case списка provider connectors через query repository."""

    def __init__(
        self,
        repository: ProviderConnectorQueryRepositoryProtocol,
    ) -> None:
        """Инициализирует use case query repository connector-ов."""
        self._repository = repository

    async def __call__(self, tenant_id: EntityIdVO) -> ProviderConnectorCatalogDTO:
        """Возвращает DTO каталога provider connectors tenant."""
        return ProviderConnectorCatalogDTO(
            connectors=await self._repository.list_connectors(tenant_id=tenant_id),
            message_types=await self._repository.list_message_types(
                tenant_id=tenant_id,
            ),
        )


__all__ = [
    "ListProviderConnectorsUseCase",
    "ListProviderConnectorsUseCaseProtocol",
]
