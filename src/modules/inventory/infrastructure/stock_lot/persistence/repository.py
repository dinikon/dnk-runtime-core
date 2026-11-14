from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.stock_lot.aggregate import StockLot
from src.modules.inventory.domain.stock_lot.error import (
    StockLotNumberAlreadyExistsError,
    StockLotNotFoundError,
)
from src.modules.inventory.domain.stock_lot.value_object.identifier import StockLotIdVO
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

    async def get_for_update(
        self, identifier: StockLotIdVO, *, inventory_item_id: InventoryItemIdVO
    ) -> StockLot | None:
        """Блокирует партию после корня SKU и перечитывает identity map после ожидания."""
        statement = (
            select(StockLotModel)
            .where(
                StockLotModel.id == identifier.uuid,
                StockLotModel.inventory_item_id == inventory_item_id.uuid,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        return StockLotMapper.to_domain(model) if model is not None else None

    async def save(self, lot: StockLot) -> None:
        """Обновляет только даты существующей партии с RETURNING без upsert и commit."""
        statement = (
            update(StockLotModel)
            .where(
                StockLotModel.id == lot.id.uuid,
                StockLotModel.inventory_item_id == lot.inventory_item_id.uuid,
            )
            .values(StockLotMapper.to_update_values(lot))
            .returning(StockLotModel.id)
        )
        if await self._session.scalar(statement) is None:
            raise StockLotNotFoundError("Партия не найдена в указанном SKU.")
