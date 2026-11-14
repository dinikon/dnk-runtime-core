from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.stock_lot.query.get_stock_lot.dto import (
    GetStockLotResultDTO,
)
from src.modules.inventory.application.stock_lot.query.get_stock_lot.query import (
    GetStockLotQuery,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.dto import (
    ListStockLotsResultDTO,
)
from src.modules.inventory.application.stock_lot.query.list_stock_lots.query import (
    ListStockLotsQuery,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)
from src.modules.inventory.infrastructure.stock_lot.persistence.query_mapper import (
    StockLotQueryMapper,
)


class SqlAlchemyStockLotQueryRepository:
    """Читает проекции партий выбранного SKU на сессии общего tenant-UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию с выбранной снаружи tenant-схемой."""
        self._session = session

    async def item_exists(self, identifier: InventoryItemIdVO) -> bool:
        """Проверяет наличие владельца без восстановления полного агрегата."""
        return (
            await self._session.scalar(
                select(InventoryItemModel.id).where(
                    InventoryItemModel.id == identifier.uuid
                )
            )
            is not None
        )

    async def get_details(self, query: GetStockLotQuery) -> GetStockLotResultDTO | None:
        """Ограничивает карточку парой ID и перечитывает identity map."""
        statement = (
            select(StockLotModel)
            .where(
                StockLotModel.id == query.lot_id.uuid,
                StockLotModel.inventory_item_id == query.inventory_item_id.uuid,
            )
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return StockLotQueryMapper.to_details(model) if model is not None else None

    async def list(self, query: ListStockLotsQuery) -> ListStockLotsResultDTO:
        """Применяет одинаковые фильтры страницы и total со стабильным порядком."""
        filters: tuple[ColumnElement[bool], ...] = (
            StockLotModel.inventory_item_id == query.inventory_item_id.uuid,
        )
        if query.search is not None:
            filters += (
                func.lower(StockLotModel.number.collate("default")).contains(
                    query.search.lower(), autoescape=True
                ),
            )
        total = await self._session.execute(
            select(func.count()).select_from(StockLotModel).where(*filters)
        )
        statement = (
            select(StockLotModel)
            .where(*filters)
            .order_by(StockLotModel.number, StockLotModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        models = (await self._session.scalars(statement)).all()
        return ListStockLotsResultDTO(
            items=tuple(StockLotQueryMapper.to_list_item(model) for model in models),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
