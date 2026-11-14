from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.stock_serial.aggregate import StockSerial
from src.modules.inventory.domain.stock_serial.error import (
    StockSerialNumberAlreadyExistsError,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel,
)
from src.modules.inventory.infrastructure.stock_serial.persistence.mapper import (
    StockSerialMapper,
)


class SqlAlchemyStockSerialRepository:
    """Записывает самостоятельный экземпляр на сессии внешнего tenant-UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию без владения транзакцией."""
        self._session = session

    async def add(self, serial: StockSerial) -> None:
        """Вставляет экземпляр и переводит только известный UNIQUE номера внутри SKU."""
        try:
            await self._session.execute(
                insert(StockSerialModel).values(
                    StockSerialMapper.to_insert_values(serial)
                )
            )
        except IntegrityError as exc:
            cause = getattr(exc.orig, "__cause__", None)
            sqlstate = getattr(exc.orig, "sqlstate", None) or getattr(
                cause, "sqlstate", None
            )
            constraint = getattr(exc.orig, "constraint_name", None) or getattr(
                cause, "constraint_name", None
            )
            if sqlstate == "23505" and constraint == "uq_stock_serials_item_number":
                raise StockSerialNumberAlreadyExistsError(
                    "Номер экземпляра уже занят внутри этого SKU."
                ) from exc
            raise
