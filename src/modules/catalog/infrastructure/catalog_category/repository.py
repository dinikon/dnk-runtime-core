from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.infrastructure.catalog_category.tree_lock import (
    lock_category_tree,
)
from sqlalchemy import select, insert, update, delete, exists, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.catalog_category import (
    CatalogCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_category_translation import (
    CatalogCategoryTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_category import (
    CatalogItemCategoryModel,
)
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.catalog_category.aggregate import CatalogCategory
from src.modules.catalog.infrastructure.catalog_category.mapper import (
    CatalogCategoryMapper,
)
from src.modules.catalog.domain.error import CatalogNotFoundError


class SqlAlchemyCatalogCategoryRepository:
    """Хранит агрегаты каталога в транзакции вызывающего сценария."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает зависимости текущего сценария."""
        self.session = session

    async def lock_tree(self, tenant_id: EntityIdVO) -> None:
        """Сериализует изменения дерева текущего tenant."""
        await lock_category_tree(self.session, tenant_id, shared=False)

    async def parents(self) -> dict[CatalogCategoryIdVO, CatalogCategoryIdVO | None]:
        """Читает связи с родителями для проверки переноса ветки."""
        rows = await self.session.execute(
            select(CatalogCategoryModel.id, CatalogCategoryModel.parent_id)
        )
        return {
            CatalogCategoryIdVO(key): CatalogCategoryIdVO(parent) if parent else None
            for key, parent in rows
        }

    async def get(self, identifier: CatalogCategoryIdVO) -> CatalogCategory:
        """Загружает категорию и её переводы по идентификатору."""
        node = await self.session.get(CatalogCategoryModel, identifier.uuid)
        if node is None:
            raise CatalogNotFoundError("Категория отсутствует.")
        names = await self.session.execute(
            select(
                CatalogCategoryTranslationModel.locale,
                CatalogCategoryTranslationModel.name,
            ).where(CatalogCategoryTranslationModel.category_id == identifier.uuid)
        )
        return CatalogCategoryMapper.to_domain(node, dict(names.all()))

    async def add(self, category: CatalogCategory) -> None:
        """Записывает новый узел вместе с его названиями."""
        await self.session.execute(
            insert(CatalogCategoryModel).values(
                id=category.id.uuid,
                parent_id=category.parent_id.uuid if category.parent_id else None,
                is_default=category.is_default,
            )
        )
        await self._insert_names(category)

    async def save(self, category: CatalogCategory) -> None:
        """Сохраняет изменённое положение и переводы категории."""
        await self.session.execute(
            update(CatalogCategoryModel)
            .where(CatalogCategoryModel.id == category.id.uuid)
            .values(parent_id=category.parent_id.uuid if category.parent_id else None)
        )
        await self.session.execute(
            delete(CatalogCategoryTranslationModel).where(
                CatalogCategoryTranslationModel.category_id == category.id.uuid
            )
        )
        await self._insert_names(category)

    async def _insert_names(self, category: CatalogCategory) -> None:
        """Сохраняет локализованные названия узла."""
        await self.session.execute(
            insert(CatalogCategoryTranslationModel),
            [
                dict(category_id=category.id.uuid, locale=code, name=translation.name)
                for code, translation in category.translations.items()
            ],
        )

    async def has_items(self, identifier: CatalogCategoryIdVO) -> bool:
        """Проверяет использование в основных и дополнительных назначениях."""
        return bool(
            await self.session.scalar(
                select(
                    exists().where(
                        CatalogItemCategoryModel.category_id == identifier.uuid
                    )
                )
            )
        )

    async def set_default(self, identifier: CatalogCategoryIdVO) -> None:
        """Меняет ссылку для создаваемых карточек."""
        await self.session.execute(
            update(CatalogCategoryModel)
            .where(
                or_(
                    CatalogCategoryModel.is_default,
                    CatalogCategoryModel.id == identifier.uuid,
                )
            )
            .values(is_default=(CatalogCategoryModel.id == identifier.uuid))
        )

    async def delete(self, category: CatalogCategory) -> None:
        """Удаляет проверенную категорию с её переводами."""
        await self.session.execute(
            delete(CatalogCategoryModel).where(
                CatalogCategoryModel.id == category.id.uuid
            )
        )
