from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import (
    StockLotNumberAlreadyExistsError,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel,
)
from src.modules.inventory.infrastructure.stock_lot.persistence.mapper import (
    StockLotMapper,
)


class SqlAlchemyStockLotRepository:
    """Записывает самостоятельную партию на сессии внешнего tenant-UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию без владения транзакцией."""
        self._session = session

    async def add(self, lot: StockLot) -> None:
        """Вставляет партию и переводит только известный UNIQUE номера внутри SKU."""
        try:
            await self._session.execute(
                insert(StockLotModel).values(StockLotMapper.to_insert_values(lot))
            )
        except IntegrityError as exc:
            cause = getattr(exc.orig, "__cause__", None)
            sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(
                cause, "sqlstate", None
            )
            constraint = getattr(exc.orig, "constraint_name", None) or getattr(
                cause, "constraint_name", None
            )
            if sqlstate == "23505" and constraint == "uq_stock_lots_item_number":
                raise StockLotNumberAlreadyExistsError(
                    "Номер партии уже занят внутри этого SKU."
                ) from exc
            raise
