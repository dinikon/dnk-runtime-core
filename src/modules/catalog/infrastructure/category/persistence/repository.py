from hashlib import blake2b
from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.error import (
    CategoryIdentifierAlreadyExistsError,
    CategoryInUseError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.domain.category.value_object.translation import (
    CategoryTranslationVO,
)
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel
from src.modules.catalog.infrastructure.persistence.models.category_content import (
    CategoryContentModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_category import (
    ProductCategoryModel,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyCategoryRepository:
    """Хранит дерево в общей tenant-сессии; транзакцией владеет UoW."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_tree(self, tenant_id: EntityIdVO) -> None:
        key = int.from_bytes(
            blake2b(
                b"catalog-category-tree:" + tenant_id.uuid.bytes, digest_size=8
            ).digest(),
            byteorder="big",
            signed=True,
        )
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": key}
        )

    async def add(self, category: Category) -> None:
        try:
            await self._session.execute(
                insert(CategoryModel).values(
                    id=category.id.uuid,
                    parent_id=category.parent_id.uuid if category.parent_id else None,
                    created_at=category.created_at,
                    updated_at=category.updated_at,
                    created_by=category.created_by.uuid,
                    updated_by=category.updated_by.uuid,
                )
            )
            await self._session.execute(
                insert(CategoryContentModel),
                [
                    {
                        "category_id": category.id.uuid,
                        "locale_code": item.locale.value,
                        "name": item.name,
                    }
                    for item in category.translations.values()
                ],
            )
        except IntegrityError as exc:
            original = exc.orig
            constraint = getattr(original, "constraint_name", None) or getattr(
                getattr(original, "__cause__", None), "constraint_name", None
            )
            if (
                getattr(original, "sqlstate", None) == "23505"
                and constraint == "pk_catalog_categories"
            ):
                raise CategoryIdentifierAlreadyExistsError(
                    "Category identifier already exists."
                ) from exc
            raise

    async def get_for_update(self, category_id: CategoryIdVO) -> Category | None:
        row = (
            await self._session.execute(
                select(CategoryModel)
                .where(CategoryModel.id == category_id.uuid)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        translations = (
            (
                await self._session.execute(
                    select(CategoryContentModel).where(
                        CategoryContentModel.category_id == category_id.uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        return Category.restore(
            category_id=CategoryIdVO.from_value(row.id),
            parent_id=CategoryIdVO.from_value(row.parent_id) if row.parent_id else None,
            translations=tuple(
                CategoryTranslationVO(CategoryLocaleVO(item.locale_code), item.name)
                for item in translations
            ),
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=EntityIdVO.from_value(row.created_by),
            updated_by=EntityIdVO.from_value(row.updated_by),
        )

    async def exists(self, category_id: CategoryIdVO) -> bool:
        return (
            await self._session.scalar(
                select(CategoryModel.id).where(CategoryModel.id == category_id.uuid)
            )
        ) is not None

    async def is_descendant(
        self, candidate_id: CategoryIdVO, ancestor_id: CategoryIdVO
    ) -> bool:
        # Поднимаемся от кандидата к корню одним рекурсивным запросом.
        ancestors = (
            select(CategoryModel.id, CategoryModel.parent_id)
            .where(CategoryModel.id == candidate_id.uuid)
            .cte("category_ancestors", recursive=True)
        )
        ancestors = ancestors.union_all(
            select(CategoryModel.id, CategoryModel.parent_id).join(
                ancestors, CategoryModel.id == ancestors.c.parent_id
            )
        )
        return (
            await self._session.scalar(
                select(ancestors.c.id)
                .where(ancestors.c.id == ancestor_id.uuid)
                .limit(1)
            )
        ) is not None

    async def save_parent(self, category: Category) -> None:
        await self._session.execute(
            update(CategoryModel)
            .where(CategoryModel.id == category.id.uuid)
            .values(
                parent_id=category.parent_id.uuid if category.parent_id else None,
                updated_at=category.updated_at,
                updated_by=category.updated_by.uuid,
            )
        )

    async def save_translation(
        self, category: Category, locale: CategoryLocaleVO
    ) -> None:
        value = category.translations[locale.value]
        statement = pg_insert(CategoryContentModel).values(
            category_id=category.id.uuid, locale_code=locale.value, name=value.name
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                constraint="pk_catalog_category_contents", set_={"name": value.name}
            )
        )
        await self._session.execute(
            update(CategoryModel)
            .where(CategoryModel.id == category.id.uuid)
            .values(updated_at=category.updated_at, updated_by=category.updated_by.uuid)
        )

    async def has_children_or_products(self, category_id: CategoryIdVO) -> bool:
        child = await self._session.scalar(
            select(CategoryModel.id)
            .where(CategoryModel.parent_id == category_id.uuid)
            .limit(1)
        )
        if child is not None:
            return True
        product = await self._session.scalar(
            select(ProductCategoryModel.product_id)
            .where(ProductCategoryModel.category_id == category_id.uuid)
            .limit(1)
        )
        return product is not None

    async def delete(self, category_id: CategoryIdVO) -> None:
        try:
            await self._session.execute(
                delete(CategoryModel).where(CategoryModel.id == category_id.uuid)
            )
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise CategoryInUseError("Category has children or products.") from exc
            raise
