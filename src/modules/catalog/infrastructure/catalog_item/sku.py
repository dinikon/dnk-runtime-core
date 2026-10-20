from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)


class SqlAlchemyCatalogItemSku:
    """Читает уникальность SKU всех видов товаров у владельца Catalog."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует сессию внешнего tenant UoW."""
        self.session = session

    async def in_use(self, sku: str) -> bool:
        """Возвращает наличие точного кода без восстановления агрегатов."""
        return (
            await self.session.scalar(
                select(CatalogItemModel.id).where(CatalogItemModel.sku == sku).limit(1)
            )
            is not None
        )
