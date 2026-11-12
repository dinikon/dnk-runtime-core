from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.inventory_item.query.get_inventory_item.dto import (
    GetInventoryItemResultDTO,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.query import (
    GetInventoryItemQuery,
)
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)

from src.modules.inventory.application.inventory_item.query.list_inventory_items.dto import (
    ListInventoryItemsResultDTO,
)
from src.modules.inventory.application.inventory_item.query.list_inventory_items.query import (
    ListInventoryItemsQuery,
)
from src.modules.inventory.infrastructure.inventory_item.persistence.query_mapper import (
    InventoryItemQueryMapper,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)


class SqlAlchemyInventoryItemQueryRepository:
    """Читает список и total напрямую из таблицы текущего tenant."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешней сборки с выбранной tenant-схемой."""
        self._session = session

    async def get_details(
        self, query: GetInventoryItemQuery
    ) -> GetInventoryItemResultDTO | None:
        """Читает карточку и штрихкоды одной SQL-проекцией текущей схемы."""
        items = InventoryItemModel.__table__
        barcodes = ItemBarcodeModel.__table__
        result = await self._session.execute(
            select(items, barcodes.c.id.label("barcode_id"), barcodes.c.barcode)
            .select_from(
                items.outerjoin(barcodes, barcodes.c.inventory_item_id == items.c.id)
            )
            .where(items.c.id == query.inventory_item_id.uuid)
            .order_by(barcodes.c.position)
        )
        rows = result.mappings().all()
        return InventoryItemQueryMapper.to_details(rows) if rows else None

    async def list(self, query: ListInventoryItemsQuery) -> ListInventoryItemsResultDTO:
        """Применяет одинаковые фильтры к total и странице со стабильным порядком."""
        table = InventoryItemModel.__table__
        filters = (
            ()
            if query.search is None
            else (table.c.sku.contains(query.search, autoescape=True),)
        )
        total = await self._session.execute(
            select(func.count()).select_from(table).where(*filters)
        )
        rows = await self._session.execute(
            select(table)
            .where(*filters)
            .order_by(table.c.sku, table.c.id)
            .offset(query.offset)
            .limit(query.limit)
        )
        return ListInventoryItemsResultDTO(
            items=tuple(
                InventoryItemQueryMapper.to_list_item(row)
                for row in rows.mappings().all()
            ),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
