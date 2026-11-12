from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.stock_location.aggregate import StockLocation
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel,
)
from src.modules.inventory.infrastructure.stock_location.persistence.mapper import (
    StockLocationMapper,
)


class SqlAlchemyStockLocationRepository:
    """Добавляет основную локацию в общей транзакции создания склада."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего tenant-UoW."""
        self._session = session

    async def add(self, location: StockLocation) -> None:
        """Вставляет адрес; технические ошибки передаёт внешней границе UoW."""
        await self._session.execute(
            insert(StockLocationModel).values(
                StockLocationMapper.to_insert_values(location)
            )
        )
