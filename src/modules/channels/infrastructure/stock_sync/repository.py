from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.stock_sync.aggregate import StockSync
from src.modules.channels.infrastructure.stock_sync.mapper import to_domain, to_values
from src.modules.channels.infrastructure.persistence.models.stock_sync import (
    StockSyncModel,
)


class SqlAlchemyStockSyncRepository:
    """Пишет состояния под общей блокировкой Channel."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего UoW."""
        self.session = session

    async def get(self, publication_id: EntityIdVO) -> StockSync | None:
        """Возвращает независимый доменный экземпляр."""
        row = await self.session.scalar(
            select(StockSyncModel)
            .where(StockSyncModel.publication_id == publication_id.uuid)
            .execution_options(populate_existing=True)
        )
        return to_domain(row) if row else None

    async def save(self, state: StockSync) -> None:
        """Атомарно сохраняет поколение; commit выполняется снаружи."""
        values = to_values(state)
        statement = insert(StockSyncModel).values(**values)
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=["publication_id"], set_=values
            )
        )
