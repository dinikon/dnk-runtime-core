from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)


class SqlAlchemyStockOwnerUsage:
    """Реализует публичный контракт использования компании без загрузки документов."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую tenant-сессию."""
        self._session = session

    async def is_owner_used(self, identifier: UUID) -> bool:
        """Учитывает все статусы и виды документов."""
        statement = select(
            select(StockDocumentModel.id)
            .where(StockDocumentModel.owner_id == identifier)
            .exists()
        )
        return (await self._session.execute(statement)).scalar_one()
