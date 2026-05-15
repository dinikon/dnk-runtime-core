from typing import Protocol

from src.modules.communication.application.provider_connection.dto import (
    ProviderConnectionDTO,
)
from src.modules.shared import EntityIdVO


class ProviderConnectionQueryRepositoryProtocol(Protocol):
    """Порт query-чтения provider connections."""

    async def list_connections(
        self,
        *,
        tenant_id: EntityIdVO,
    ) -> list[ProviderConnectionDTO]:
        """Возвращает DTO provider connections tenant."""
        ...


__all__ = ["ProviderConnectionQueryRepositoryProtocol"]
