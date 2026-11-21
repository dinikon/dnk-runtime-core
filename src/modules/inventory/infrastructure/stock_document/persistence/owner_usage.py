from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel,
)
from uuid import UUID
from sqlalchemy import select, or_
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
        """Учитывает документы, позиции и факты независимо от статуса и текущего количества."""
        statement = select(
            or_(
                select(StockDocumentModel.id)
                .where(StockDocumentModel.owner_id == identifier)
                .exists(),
                select(StockPositionModel.id)
                .where(StockPositionModel.owner_id == identifier)
                .exists(),
                select(StockExecutionModel.id)
                .where(StockExecutionModel.owner_id == identifier)
                .exists(),
            )
        )
        return (await self._session.execute(statement)).scalar_one()
