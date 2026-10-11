from typing import Protocol
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)


class CatalogItemOwnerLookupPort(Protocol):
    """Разрешает корень по единому item ID без загрузки ребёнка как агрегата."""

    async def root_id(self, item_id: CatalogItemIdVO) -> CatalogItemIdVO:
        """Возвращает собственный ID корня либо parent ID VARIANT."""
        ...
