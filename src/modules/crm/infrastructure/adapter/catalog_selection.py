from uuid import UUID
from src.modules.catalog.application.catalog_item.query.get_catalog_item.handler import (
    GetCatalogItemHandler,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.query import (
    GetCatalogItemQuery,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.crm.application.basket.port.catalog_selection import (
    CatalogSelectionDTO,
)


class CatalogSelectionAdapter:
    """Использует публичный read-контракт Catalog, не его модели."""

    def __init__(self, reader: GetCatalogItemHandler) -> None:
        """Принимает готовый сценарий чтения Catalog."""
        self._reader = reader

    async def get(
        self, tenant_id: UUID, item_id: UUID, locale: str
    ) -> CatalogSelectionDTO:
        """Преобразует снимок без повторного ценообразования."""
        result = await self._reader.execute(
            GetCatalogItemQuery(EntityIdVO(tenant_id), CatalogItemIdVO(item_id), locale)
        )
        item = result.item
        return CatalogSelectionDTO(
            item.id,
            (item.content or {}).get("title", ""),
            item.sku,
            "service" if item.virtual else "product",
        )
