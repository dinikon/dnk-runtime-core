from uuid import UUID
from sqlalchemy import select
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
                    select(Line.id).where(Line.inventory_item_id == identifier).exists()
                )
            )
        ).scalar_one()

    async def serial_has_history(self, identifier: UUID) -> bool:
        """Не ограничивает историю текущим положительным остатком."""
        return (
            await self._session.execute(
                select(select(Line.id).where(Line.serial_id == identifier).exists())
            )
        ).scalar_one()
