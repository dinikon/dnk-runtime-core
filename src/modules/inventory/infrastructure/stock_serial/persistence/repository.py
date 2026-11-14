from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_serial.value_object.identifier import (
    StockSerialIdVO,
)
from src.modules.inventory.domain.stock_serial.error import StockSerialNotFoundError
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
            self._raise_number_conflict(exc)
            raise

    async def get_for_update(
        self, identifier: StockSerialIdVO, *, inventory_item_id: InventoryItemIdVO
    ) -> StockSerial | None:
        """Блокирует экземпляр после SKU и перечитывает identity map после ожидания."""
        statement = (
            select(StockSerialModel)
            .where(
                StockSerialModel.id == identifier.uuid,
                StockSerialModel.inventory_item_id == inventory_item_id.uuid,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return StockSerialMapper.to_domain(model) if model is not None else None

    async def save(self, serial: StockSerial) -> None:
        """Обновляет номер и партию существующей строки через RETURNING без upsert/commit."""
        statement = (
            update(StockSerialModel)
            .where(
                StockSerialModel.id == serial.id.uuid,
                StockSerialModel.inventory_item_id == serial.inventory_item_id.uuid,
            )
            .values(StockSerialMapper.to_update_values(serial))
            .returning(StockSerialModel.id)
        )
        try:
            identifier = await self._session.scalar(statement)
        except IntegrityError as exc:
            self._raise_number_conflict(exc)
            raise
        if identifier is None:
            raise StockSerialNotFoundError("Экземпляр не найден в указанном SKU.")

    @staticmethod
    def _raise_number_conflict(error: IntegrityError) -> None:
        """Переводит только известный UNIQUE, сохраняя исходную причину конфликта."""
        cause = getattr(error.orig, "__cause__", None)
        sqlstate = getattr(error.orig, "sqlstate", None) or getattr(
            cause, "sqlstate", None
        )
        constraint = getattr(error.orig, "constraint_name", None) or getattr(
            cause, "constraint_name", None
        )
        if sqlstate == "23505" and constraint == "uq_stock_serials_item_number":
            raise StockSerialNumberAlreadyExistsError(
                "Номер экземпляра уже занят внутри этого SKU."
            ) from error
