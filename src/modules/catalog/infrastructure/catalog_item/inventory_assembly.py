from src.modules.inventory.infrastructure.inventory_item.persistence.repository import (
    SqlAlchemyInventoryItemRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.catalog_item.inventory_service import (
    CatalogItemInventoryService,
)
from src.modules.catalog.infrastructure.catalog_item.inventory import (
    InventoryCatalogItems,
)
from src.modules.catalog.infrastructure.catalog_item.sku import SqlAlchemyCatalogItemSku
from src.modules.inventory.application.inventory_item.reference_service import (
    InventoryItemReferenceService,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.references import (
    SqlAlchemyInventoryItemReferences,
)
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator


def build_catalog_inventory(session: AsyncSession) -> CatalogItemInventoryService:
    """Собирает межмодульный сценарий на одной уже открытой tenant-сессии."""
    references = InventoryItemReferenceService(
        SqlAlchemyInventoryItemRepository(session),
        SqlAlchemyInventoryItemReferences(session),
        UUID7Generator(),
    )
    return CatalogItemInventoryService(
        InventoryCatalogItems(references), SqlAlchemyCatalogItemSku(session)
    )
