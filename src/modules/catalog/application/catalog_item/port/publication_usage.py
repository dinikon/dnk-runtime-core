from typing import Protocol
from uuid import UUID


class CatalogPublicationUsagePort(Protocol):
    """Факты внешнего использования, не зависящие от Channels моделей."""

    async def used(self, root_id: UUID, position_id: UUID | None = None) -> bool:
        """Проверяет использование под уже взятой семейной блокировкой."""
        ...
