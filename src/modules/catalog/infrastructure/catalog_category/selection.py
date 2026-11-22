from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.infrastructure.catalog_category.tree_lock import (
    lock_category_tree,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.categories import (
    CatalogItemCategoriesVO,
)
from src.modules.catalog.domain.error import InvalidCatalogValueError
from src.modules.catalog.infrastructure.persistence.models.catalog_category import (
    CatalogCategoryModel,
)


class SqlAlchemyCatalogCategorySelection:
    """Разрешает ссылки карточки под общей блокировкой настроек текущего tenant."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает зависимости текущего сценария."""
        self.session = session

    async def default_id(self, tenant_id: EntityIdVO) -> CatalogCategoryIdVO:
        """Проверяет выбранные ссылки или подставляет основную категорию новых товаров."""
        await lock_category_tree(self.session, tenant_id, shared=True)
        default = (
            await self.session.execute(
                select(CatalogCategoryModel.id).where(CatalogCategoryModel.is_default)
            )
        ).scalar_one()
        return CatalogCategoryIdVO(default)

    async def ensure_exist(
        self, tenant_id: EntityIdVO, categories: CatalogItemCategoriesVO
    ) -> None:
        """Удерживает дерево от удаления выбранных категорий до записи товара."""
        await lock_category_tree(self.session, tenant_id, shared=True)
        ids = [
            value.uuid
            for value in (
                categories.primary_category_id,
                *categories.additional_category_ids,
            )
        ]
        found = (
            await self.session.scalars(
                select(CatalogCategoryModel.id).where(CatalogCategoryModel.id.in_(ids))
            )
        ).all()
        if len(found) != len(ids):
            raise InvalidCatalogValueError(
                "Выбранная категория отсутствует.", ("categories",)
            )
