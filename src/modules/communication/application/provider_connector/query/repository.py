from typing import Protocol

from src.modules.communication.application.provider_connector.dto import (
    ProviderConnectorDTO,
    ProviderMessageTypeDTO,
)
from src.modules.shared import EntityIdVO


class ProviderConnectorQueryRepositoryProtocol(Protocol):
    """Порт query-чтения provider connectors."""

    async def list_connectors(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[ProviderConnectorDTO]:
        """Возвращает DTO provider connectors tenant."""
        ...

    async def list_message_types(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[ProviderMessageTypeDTO]:
        """Возвращает DTO provider message types tenant."""
        ...


__all__ = ["ProviderConnectorQueryRepositoryProtocol"]
