from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.product.error import ProductCategoryNotFoundError
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel


class SqlAlchemyCategoryReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def require_all(self, category_ids: tuple[UUID, ...]) -> None:
        if not category_ids:
            return
        found = set(
            (
                await self._session.execute(
                    select(CategoryModel.id)
                    .where(CategoryModel.id.in_(category_ids))
                    .order_by(CategoryModel.id)
                    .with_for_update(read=True, key_share=True)
                )
            )
            .scalars()
            .all()
        )
        if found != set(category_ids):
            raise ProductCategoryNotFoundError("Category not found.")
