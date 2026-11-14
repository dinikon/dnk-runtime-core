from sqlalchemy import ColumnElement, Nullable, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.application.stock_serial.query.get_stock_serial.dto import (
    GetStockSerialResultDTO,
)
from src.modules.inventory.application.stock_serial.query.get_stock_serial.query import (
    GetStockSerialQuery,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.dto import (
    ListStockSerialsResultDTO,
)
from src.modules.inventory.application.stock_serial.query.list_stock_serials.query import (
    ListStockSerialsQuery,
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
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel,
)
from src.modules.inventory.infrastructure.stock_serial.persistence.query_mapper import (
    StockSerialQueryMapper,
)


class SqlAlchemyStockSerialQueryRepository:
    """Читает проекции серийных экземпляров выбранного SKU на сессии общего tenant-UoW."""

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

    async def get_details(
        self, query: GetStockSerialQuery
    ) -> GetStockSerialResultDTO | None:
        """Ограничивает карточку парой ID и перечитывает identity map."""
        statement = (
            select(StockSerialModel, Nullable(StockLotModel))
            .outerjoin(
                StockLotModel,
                and_(
                    StockLotModel.id == StockSerialModel.lot_id,
                    StockLotModel.inventory_item_id
                    == StockSerialModel.inventory_item_id,
                ),
            )
            .where(
                StockSerialModel.id == query.serial_id.uuid,
                StockSerialModel.inventory_item_id == query.inventory_item_id.uuid,
            )
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(statement)).one_or_none()
        return (
            StockSerialQueryMapper.to_details(row[0], row[1])
            if row is not None
            else None
        )

    async def list(self, query: ListStockSerialsQuery) -> ListStockSerialsResultDTO:
        """Применяет одинаковые фильтры страницы и total со стабильным порядком."""
        filters: tuple[ColumnElement[bool], ...] = (
            StockSerialModel.inventory_item_id == query.inventory_item_id.uuid,
        )
        if query.search is not None:
            filters += (
                func.lower(StockSerialModel.number.collate("default")).contains(
                    query.search.lower(), autoescape=True
                ),
            )
        total = await self._session.execute(
            select(func.count()).select_from(StockSerialModel).where(*filters)
        )
        statement = (
            select(StockSerialModel, Nullable(StockLotModel))
            .outerjoin(
                StockLotModel,
                and_(
                    StockLotModel.id == StockSerialModel.lot_id,
                    StockLotModel.inventory_item_id
                    == StockSerialModel.inventory_item_id,
                ),
            )
            .where(*filters)
            .order_by(StockSerialModel.number, StockSerialModel.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        return ListStockSerialsResultDTO(
            items=tuple(
                StockSerialQueryMapper.to_list_item(model, lot) for model, lot in rows
            ),
            total=total.scalar_one(),
            offset=query.offset,
            limit=query.limit,
        )
