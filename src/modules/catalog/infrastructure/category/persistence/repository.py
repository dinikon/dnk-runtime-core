from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.error import CategoryNotFoundError
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel
from src.modules.catalog.infrastructure.persistence.models.category_translation import (
    CategoryTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_category import (
    ProductCategoryModel,
)
from src.modules.catalog.infrastructure.category.persistence.mapper import (
    CategoryMapper,
)


class SqlAlchemyCategoryRepository:
    """Хранит полный Category на общей tenant-сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию без управления schema и commit."""
        self._session = session

    async def get(self, identifier: CategoryIdVO) -> Category:
        """Читает корень и переводы для доменного восстановления."""
        row = (
            (
                await self._session.execute(
                    select(CategoryModel.__table__).where(
                        CategoryModel.id == identifier.uuid
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CategoryNotFoundError("Объект отсутствует.")
        labels = dict(
            (
                await self._session.execute(
                    select(
                        CategoryTranslationModel.locale, CategoryTranslationModel.label
                    ).where(CategoryTranslationModel.category_id == identifier.uuid)
                )
            ).all()
        )
        return CategoryMapper.to_domain(row, labels)

    async def add(self, entity: Category) -> None:
        """Добавляет корень и его переводы без commit."""
        await self._session.execute(
            insert(CategoryModel).values(CategoryMapper.to_insert_values(entity))
        )
        await self._save_translations(entity)

    async def save(self, entity: Category) -> None:
        """Сохраняет состояние, проверенное доменными методами."""
        await self._session.execute(
            update(CategoryModel)
            .where(CategoryModel.id == entity.id.uuid)
            .values(CategoryMapper.to_update_values(entity))
        )
        await self._save_translations(entity)

    async def _save_translations(self, entity: Category) -> None:
        """Синхронизирует принадлежащие переводы в текущей транзакции."""
        await self._session.execute(
            delete(CategoryTranslationModel).where(
                CategoryTranslationModel.category_id == entity.id.uuid
            )
        )
        if entity.translations:
            await self._session.execute(
                insert(CategoryTranslationModel),
                [
                    {"category_id": entity.id.uuid, "locale": k, "label": v}
                    for k, v in entity.translations.items()
                ],
            )

    async def delete(self, entity: Category) -> None:
        """Удаляет корень после проверки использования доменом."""
        await self._session.execute(
            delete(CategoryModel).where(CategoryModel.id == entity.id.uuid)
        )

    async def is_used(self, identifier: CategoryIdVO) -> bool:
        """Читает наличие назначений и дочерних узлов без бизнес-решения."""
        return bool(
            await self._session.scalar(
                select(ProductCategoryModel.product_id)
                .where(ProductCategoryModel.category_id == identifier.uuid)
                .limit(1)
            )
        ) or bool(
            await self._session.scalar(
                select(CategoryModel.id)
                .where(CategoryModel.parent_id == identifier.uuid)
                .limit(1)
            )
        )
