from dataclasses import replace
from sqlalchemy import true, false, and_, or_
from src.modules.inventory.application.stock_position.query.list_stock_balances.query import (
    ListStockBalancesQuery,
)
from src.modules.inventory.application.stock_position.query.list_stock_balances.dto import (
    ListStockBalancesResultDTO,
)
from sqlalchemy import select, func, Nullable
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel as P,
)
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel as L,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel as W,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel as I,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel as Lot,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel as S,
)
from src.modules.inventory.infrastructure.persistence.models.stock_ledger_entries import (
    StockLedgerEntryModel as Entry,
)
from src.modules.inventory.infrastructure.accounting.persistence.filters import (
    dimension_filters,
)
from src.modules.inventory.infrastructure.accounting.persistence.query_mapper import (
    StockAccountingQueryMapper as Mapper,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.query import (
    ListStockPositionsQuery,
)
from src.modules.inventory.application.stock_position.query.list_stock_positions.dto import (
    ListStockPositionsResultDTO,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.query import (
    GetStockPositionQuery,
)
from src.modules.inventory.application.stock_position.query.get_stock_position.dto import (
    GetStockPositionResultDTO,
)


class SqlAlchemyStockPositionQueryRepository:
    """Читает физические позиции без блокировок записи и восстановления агрегатов."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего tenant-UoW."""
        self._session = session

    async def list(self, query: ListStockPositionsQuery) -> ListStockPositionsResultDTO:
        """Использует одинаковые фильтры страницы и total, сохраняя nullable измерения."""
        filters = dimension_filters(query.filters)
        if not query.include_zero:
            filters += (P.on_hand_qty > 0,)
        total = (
            await self._session.execute(
                select(func.count())
                .select_from(P)
                .join(L, L.id == P.location_id)
                .join(I, I.id == P.inventory_item_id)
                .outerjoin(Lot, Lot.id == P.lot_id)
                .outerjoin(S, S.id == P.serial_id)
                .where(*filters)
            )
        ).scalar_one()
        statement = (
            select(P, L, W, I, Nullable(Lot), Nullable(S))
            .join(L, L.id == P.location_id)
            .join(W, W.id == L.warehouse_id)
            .join(I, I.id == P.inventory_item_id)
            .outerjoin(Lot, Lot.id == P.lot_id)
            .outerjoin(S, S.id == P.serial_id)
            .where(*filters)
            .order_by(I.sku, L.code, P.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        return ListStockPositionsResultDTO(
            tuple(Mapper.position(*row) for row in rows),
            total,
            query.offset,
            query.limit,
        )

    async def get(
        self, query: GetStockPositionQuery
    ) -> GetStockPositionResultDTO | None:
        """Читает количество и сумму всей истории одним SQL-снимком, а не по странице журнала."""
        ledger = (
            select(func.coalesce(func.sum(Entry.quantity_delta), 0))
            .where(Entry.position_id == P.id)
            .correlate(P)
            .scalar_subquery()
        )
        statement = (
            select(P, L, W, I, Nullable(Lot), Nullable(S), ledger)
            .join(L, L.id == P.location_id)
            .join(W, W.id == L.warehouse_id)
            .join(I, I.id == P.inventory_item_id)
            .outerjoin(Lot, Lot.id == P.lot_id)
            .outerjoin(S, S.id == P.serial_id)
            .where(P.id == query.identifier)
            .execution_options(populate_existing=True)
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        p, l, w, item, lot, serial, quantity = row
        return Mapper.details(p, l, w, item, lot, serial, quantity)

    async def balances(
        self, query: ListStockBalancesQuery
    ) -> ListStockBalancesResultDTO:
        """Суммирует в NUMERIC; сворачивает LOT/SERIAL независимо, сохраняя остальные измерения."""
        filters = dimension_filters(replace(query.filters, search=None))
        if query.filters.search:
            search = query.filters.search
            filters += (
                or_(
                    I.sku.icontains(search, autoescape=True),
                    select(Lot.id)
                    .where(
                        Lot.id == P.lot_id,
                        Lot.number.icontains(search, autoescape=True),
                    )
                    .correlate(P)
                    .exists(),
                    select(S.id)
                    .where(
                        S.id == P.serial_id, S.number.icontains(search, autoescape=True)
                    )
                    .correlate(P)
                    .exists(),
                ),
            )
        if not query.include_zero:
            filters += (P.on_hand_qty > 0,)
        grouped = (
            select(
                I,
                L,
                W,
                Nullable(Lot),
                Nullable(S),
                P.owner_id,
                P.stock_status,
                P.base_uom,
                func.sum(P.on_hand_qty),
                func.count(P.id),
                func.count(func.distinct(P.lot_id)),
                func.count(func.distinct(P.serial_id)),
            )
            .select_from(P)
            .join(I, I.id == P.inventory_item_id)
            .join(L, L.id == P.location_id)
            .join(W, W.id == L.warehouse_id)
            .outerjoin(
                Lot, and_(Lot.id == P.lot_id, true() if query.group_by_lot else false())
            )
            .outerjoin(
                S,
                and_(S.id == P.serial_id, true() if query.group_by_serial else false()),
            )
            .where(*filters)
            .group_by(
                I.id, L.id, W.id, Lot.id, S.id, P.owner_id, P.stock_status, P.base_uom
            )
        )
        total = (
            await self._session.execute(
                select(func.count()).select_from(grouped.subquery())
            )
        ).scalar_one()
        statement = (
            grouped.order_by(
                I.sku,
                W.id,
                L.id,
                P.owner_id,
                P.stock_status,
                P.base_uom,
                Lot.id,
                S.id,
                I.id,
            )
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        return ListStockBalancesResultDTO(
            tuple(
                Mapper.balance(
                    item,
                    location,
                    warehouse,
                    lot,
                    serial,
                    owner,
                    status,
                    uom,
                    quantity,
                    count,
                    lot_count,
                    serial_count,
                    query.group_by_lot,
                    query.group_by_serial,
                )
                for item, location, warehouse, lot, serial, owner, status, uom, quantity, count, lot_count, serial_count in rows
            ),
            total,
            query.offset,
            query.limit,
        )
