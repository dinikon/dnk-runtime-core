from sqlalchemy import ColumnElement, Nullable, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.inventory_item.query.get_inventory_item.dto import (
    GetInventoryItemResultDTO,
)
from src.modules.inventory.application.inventory_item.query.get_inventory_item.query import (
    GetInventoryItemQuery,
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
from src.modules.inventory.infrastructure.persistence.models.item_barcode import (
    ItemBarcodeModel,
)


class SqlAlchemyInventoryItemQueryRepository:
    """Читает проекции списка и карточки для текущего tenant без восстановления агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешней сборки с выбранной tenant-схемой."""
        self._session = session

    async def get_details(
        self, query: GetInventoryItemQuery
    ) -> GetInventoryItemResultDTO | None:
        """Читает карточку и штрихкоды одной SQL-проекцией текущей схемы."""
        statement = (
            select(InventoryItemModel, Nullable(ItemBarcodeModel))
            .outerjoin(
                ItemBarcodeModel,
                ItemBarcodeModel.inventory_item_id == InventoryItemModel.id,
            )
            .where(InventoryItemModel.id == query.inventory_item_id.uuid)
            .order_by(ItemBarcodeModel.position)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return None
        model = rows[0][0]
        barcodes = tuple(barcode for _, barcode in rows if barcode is not None)
        return InventoryItemQueryMapper.to_details(model, barcodes)

    async def list(self, query: ListInventoryItemsQuery) -> ListInventoryItemsResultDTO:
        """Применяет одинаковые фильтры к total и странице со стабильным порядком."""
        filters: tuple[ColumnElement[bool], ...] = (
            ()
            if query.search is None
            else (InventoryItemModel.sku.contains(query.search, autoescape=True),)
        )
        total = await self._session.execute(
            select(func.count()).select_from(InventoryItemModel).where(*filters)
        )
        statement = (
            select(InventoryItemModel)
            .where(*filters)
            .order_by(InventoryItemModel.sku, InventoryItemModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        models = (await self._session.scalars(statement)).all()
        return ListInventoryItemsResultDTO(
            items=tuple(
                InventoryItemQueryMapper.to_list_item(model) for model in models
            ),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
