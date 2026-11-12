from typing import Protocol
from uuid import UUID

from src.modules.catalog.application.catalog_item.inventory_item_selection import (
    CatalogInventoryItemSelection,
    CatalogInventoryItemReference,
)


class CatalogInventoryItemPort(Protocol):
    """Изолирует Catalog от доменной модели и хранения Inventory."""

    def normalize(self, sku: str) -> str:
        """Валидирует код без записи позиции, включая предварительную проверку импорта."""
        ...

    async def resolve(
        self, selection: CatalogInventoryItemSelection
    ) -> CatalogInventoryItemReference | None:
        """Выбирает или создаёт позицию в уже открытой общей транзакции."""
        ...

    async def find_id(self, sku: str) -> UUID | None:
        """Ищет ID по точному коду без создания складской позиции."""
        ...

    async def codes(self, identifiers: tuple[UUID, ...]) -> dict[UUID, str]:
        """Читает актуальные коды ссылок одним batch."""
        ...

    async def search_ids(self, search: str) -> tuple[UUID, ...]:
        """Находит полный набор ID до серверной пагинации Catalog."""
        ...
