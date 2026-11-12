from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)


class SqlAlchemyCatalogItemSku:
    """Читает только собственные связи Catalog, включая варианты и архив."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего tenant UoW."""
        self._session = session

    async def owner(self, inventory_item_id: UUID) -> UUID | None:
        """Не фильтрует связи по статусу или роли карточки."""
        return await self._session.scalar(
            select(CatalogItemModel.id)
            .where(CatalogItemModel.inventory_item_id == inventory_item_id)
            .limit(1)
        )
