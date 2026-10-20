from typing import Protocol
from uuid import UUID
from src.modules.channels.application.product_representation.contracts import (
    PublicationCatalogSourceDTO,
)


class PublicationCatalogSourcePort(Protocol):
    """Читает snapshot и блокирует публикацию перед созданием локальной связи."""

    async def source(
        self, publication_id: UUID, *, lock: bool = False
    ) -> PublicationCatalogSourceDTO:
        """Читает локальные данные и при записи сериализуется с импортом/архивом."""
        ...
