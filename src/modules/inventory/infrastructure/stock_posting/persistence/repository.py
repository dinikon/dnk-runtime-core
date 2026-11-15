from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.domain.stock_posting.aggregate import StockPosting
from src.modules.inventory.domain.stock_posting.value_object.identifier import (
    StockPostingIdVO,
)
from src.modules.inventory.infrastructure.stock_posting.persistence.mapper import (
    StockPostingMapper,
)
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel as Header,
)
from src.modules.inventory.infrastructure.persistence.models.stock_ledger_entries import (
    StockLedgerEntryModel as Entry,
)


class SqlAlchemyStockPostingRepository:
    """Хранит append-only проведение с Ledger на общей tenant-сессии."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW без собственной транзакции."""
        self._session = session

    async def add(self, posting: StockPosting) -> None:
        """Вставляет корень и принадлежащие ему записи без upsert и commit."""
        await self._session.execute(
            insert(Header).values(StockPostingMapper.to_values(posting))
        )
        await self._session.execute(
            insert(Entry), StockPostingMapper.entry_values(posting)
        )

    async def get(self, identifier: StockPostingIdVO) -> StockPosting | None:
        """Восстанавливает полный исторический факт вместе с упорядоченным Ledger."""
        model = (
            await self._session.scalars(
                select(Header)
                .where(Header.id == identifier.uuid)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        if model is None:
            return None
        entries = (
            await self._session.scalars(
                select(Entry)
                .where(Entry.posting_id == model.id)
                .order_by(Entry.position)
                .execution_options(populate_existing=True)
            )
        ).all()
        return StockPostingMapper.to_domain(model, entries)
