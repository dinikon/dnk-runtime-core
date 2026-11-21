from uuid import UUID

from src.modules.catalog.application.catalog_item.inventory_item_selection import (
    CatalogInventoryItemSelection,
    CatalogInventoryItemReference,
)
from src.modules.catalog.application.catalog_item.port.inventory import (
    CatalogInventoryItemPort,
)
from src.modules.catalog.application.catalog_item.port.sku import CatalogItemSkuPort
from src.modules.catalog.domain.error import CatalogConflictError


class CatalogItemInventoryService:
    """Координирует разрешение SKU и проверку владельца ссылки в Catalog."""

    def __init__(
        self, inventory: CatalogInventoryItemPort, links: CatalogItemSkuPort
    ) -> None:
        """Принимает порты Inventory и Catalog одного внешнего UoW."""
        self.inventory, self._links = inventory, links

    async def resolve(
        self,
        selection: CatalogInventoryItemSelection | None,
        target_id: UUID | None = None,
    ) -> CatalogInventoryItemReference | None:
        """Проверяет занятость ссылки; итоговую защиту гонки обеспечивает UNIQUE."""
        if selection is None:
            return None
        reference = await self.inventory.resolve(selection)
        if reference is not None:
            owner = await self._links.owner(reference.id)
            if owner is not None and owner != target_id:
                raise CatalogConflictError(
                    "Этот SKU уже связан с другим элементом каталога.", ("sku",)
                )
        return reference
