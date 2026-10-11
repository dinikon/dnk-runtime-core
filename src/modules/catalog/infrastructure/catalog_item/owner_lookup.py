from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.error import CatalogNotFoundError
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)


class SqlAlchemyCatalogItemOwnerLookup:
    """Определяет корень по единой идентичности item."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию внешнего UoW."""
        self._session = session

    async def root_id(self, item_id: CatalogItemIdVO) -> CatalogItemIdVO:
        """Возвращает собственный ID корня либо parent ID варианта."""
        row = (
            await self._session.execute(
                select(CatalogItemModel.id, CatalogItemModel.parent_id).where(
                    CatalogItemModel.id == item_id.uuid
                )
            )
        ).first()
        if row is None:
            raise CatalogNotFoundError("CatalogItem отсутствует.")
        return CatalogItemIdVO(row.parent_id or row.id)
