from src.modules.inventory.infrastructure.stock_document.persistence.return_origin_query_mapper import (
    ReturnOriginQueryMapper,
)
from decimal import Decimal
from sqlalchemy import select, func, Nullable
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel as Line,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_return_line import (
    StockExecutionReturnLineModel as Link,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as E,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel as W,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel as I,
)
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel as L,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel as Lot,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel as S,
)
from src.modules.inventory.application.stock_document.query.get_return_origin.query import (
    GetReturnOriginQuery,
)
from src.modules.inventory.application.stock_document.query.get_return_origin.dto import (
    GetReturnOriginResultDTO,
)


class SqlAlchemyReturnOriginQueryRepository:
    """Читает фактические строки и суммы возвратов согласованным SQL без восстановления агрегатов."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего tenant-UoW."""
        self._session = session

    async def get(
        self, query: GetReturnOriginQuery, *, direction: str
    ) -> GetReturnOriginResultDTO | None:
        """Возвращает точный накопленный итог отдельно для каждой фактической строки."""
        actual = aliased(Line)
        returned = (
            select(func.coalesce(func.sum(actual.quantity), Decimal(0)))
            .select_from(Link)
            .join(actual, actual.id == Link.execution_line_id)
            .where(Link.origin_execution_line_id == Line.id)
            .correlate(Line)
            .scalar_subquery()
        )
        statement = (
            select(
                E,
                W,
                Line,
                I,
                L,
                Nullable(Lot),
                Nullable(S),
                returned,
                Line.quantity - returned,
            )
            .join(W, W.id == E.warehouse_id)
            .join(Line, Line.execution_id == E.id)
            .join(I, I.id == Line.inventory_item_id)
            .join(L, L.id == Line.location_id)
            .outerjoin(Lot, Lot.id == Line.lot_id)
            .outerjoin(S, S.id == Line.serial_id)
            .where(E.id == query.execution_id)
            .order_by(Line.position, Line.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return None
        return ReturnOriginQueryMapper.to_details(
            rows[0][0],
            rows[0][1],
            direction=direction,
            lines=tuple(
                ReturnOriginQueryMapper.to_line(
                    line, item, location, lot, serial, returned, remaining
                )
                for _, _, line, item, location, lot, serial, returned, remaining in rows
            ),
        )
