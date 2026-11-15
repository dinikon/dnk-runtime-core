from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.domain.stock_document.aggregate import StockDocument
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.mapper import (
    StockDocumentMapper,
)


class SqlAlchemyStockDocumentRepository:
    """Сохраняет новый документ и дочерние строки в общей tenant-транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW."""
        self._session = session

    async def add(self, document: StockDocument) -> None:
        """Вставляет корень и строки без upsert и самостоятельного commit."""
        lines = StockDocumentMapper.to_line_insert_values(document)
        await self._session.execute(
            insert(StockDocumentModel).values(
                StockDocumentMapper.to_insert_values(document)
            )
        )
        if lines:
            await self._session.execute(insert(StockDocumentLineModel), lines)
