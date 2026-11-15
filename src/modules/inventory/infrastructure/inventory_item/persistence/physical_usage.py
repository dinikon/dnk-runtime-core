from src.modules.inventory.domain.inventory_item.accounting_usage import (
    InventoryItemAccountingUsage,
)
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.stock_dates import StockDatesVO
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel as Position,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel as Lot,
)
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel as Line,
)


class SqlAlchemyPhysicalInventoryUsage:
    """Читает факты использования по собственным моделям Inventory на общей сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию внешнего UoW."""
        self._session = session

    async def item_has_history(self, identifier: UUID) -> bool:
        """Учитывает любое сохранённое исполнение, в том числе уже исчерпанный запас."""
        return (
            await self._session.execute(
                select(
                    or_(
                        select(Line.id)
                        .where(Line.inventory_item_id == identifier)
                        .exists(),
                        select(Position.id)
                        .where(Position.inventory_item_id == identifier)
                        .exists(),
                    )
                )
            )
        ).scalar_one()

    async def serial_has_history(self, identifier: UUID) -> bool:
        """Не ограничивает историю текущим положительным остатком."""
        return (
            await self._session.execute(
                select(
                    or_(
                        select(Line.id).where(Line.serial_id == identifier).exists(),
                        select(Position.id)
                        .where(Position.serial_id == identifier)
                        .exists(),
                    )
                )
            )
        ).scalar_one()

    async def item_state(self, identifier: UUID) -> InventoryItemAccountingUsage:
        """Передаёт доменной проверке факты без вычисления бизнес-совместимости в SQL."""
        has_history = await self.item_has_history(identifier)
        quantities = (
            await self._session.scalars(
                select(Position.on_hand_qty)
                .where(Position.inventory_item_id == identifier)
                .distinct()
            )
        ).all()
        statement = (
            select(Lot.manufactured_on, Lot.expires_on)
            .join(Position, Position.lot_id == Lot.id)
            .where(Position.inventory_item_id == identifier, Position.on_hand_qty > 0)
            .distinct()
        )
        dates = (await self._session.execute(statement)).all()
        return InventoryItemAccountingUsage(
            has_history,
            tuple(QuantityVO(q) for q in quantities),
            tuple(
                StockDatesVO(manufactured, expires) for manufactured, expires in dates
            ),
        )

    async def lot_has_positive_stock(self, identifier: UUID) -> bool:
        """Читает наличие положительного физического запаса партии во всех измерениях."""
        return (
            await self._session.execute(
                select(
                    select(Position.id)
                    .where(Position.lot_id == identifier, Position.on_hand_qty > 0)
                    .exists()
                )
            )
        ).scalar_one()
