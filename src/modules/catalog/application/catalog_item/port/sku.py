from typing import Protocol
from uuid import UUID


class CatalogItemSkuPort(Protocol):
    """Читает владельца складской ссылки в каталоге текущего tenant."""

    async def owner(self, inventory_item_id: UUID) -> UUID | None:
        """Возвращает ID любой связанной карточки независимо от её статуса."""
        ...
