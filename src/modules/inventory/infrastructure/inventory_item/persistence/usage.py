from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.inventory_item.port.usage import (
    InventoryItemUsagePort,
)
from src.modules.inventory.domain.inventory_item.deletion_usage import (
    InventoryItemDeletionUsage,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)


class SqlAlchemyInventoryItemUsage:
    """Дополняет публичное чтение Catalog локальным фактом существования партий."""

    def __init__(self, session: AsyncSession, catalog: InventoryItemUsagePort) -> None:
        """Принимает общий tenant-UoW и адаптер Catalog на той же транзакции."""
        self._session = session
        self._catalog = catalog

    async def get(self, identifier: InventoryItemIdVO) -> InventoryItemDeletionUsage:
        """Читает необходимые факты без загрузки партий или чужих ORM-моделей."""
        catalog = await self._catalog.get(identifier)
        statement = select(
            select(StockLotModel.id)
            .where(StockLotModel.inventory_item_id == identifier.uuid)
            .exists()
        )
        result = await self._session.execute(statement)
        return InventoryItemDeletionUsage(
            has_catalog_items=catalog.has_catalog_items,
            has_stock_lots=result.scalar_one(),
        )
