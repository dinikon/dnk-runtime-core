from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.modules.catalog.application.category.query.get_category.dto import (
    CategoryDetailsDTO,
    CategoryTranslationDTO,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    CategoryListItemDTO,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel
from src.modules.catalog.infrastructure.persistence.models.category_content import (
    CategoryContentModel,
)


class SqlAlchemyCategoryQueryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_details(
        self, category_id: CategoryIdVO, locale: CategoryLocaleVO
    ) -> CategoryDetailsDTO | None:
        rows = (
            await self._session.execute(
                select(CategoryModel, CategoryContentModel)
                .outerjoin(
                    CategoryContentModel,
                    CategoryContentModel.category_id == CategoryModel.id,
                )
                .where(CategoryModel.id == category_id.uuid)
                .order_by(CategoryContentModel.locale_code)
            )
        ).all()
        if not rows:
            return None
        category = rows[0][0]
        translations = tuple(
            CategoryTranslationDTO(item.locale_code, item.name)
            for _, item in rows
            if item is not None
        )
        return CategoryDetailsDTO(
            id=category.id,
            parent_id=category.parent_id,
            requested_locale=locale.value,
            name=next(
                (item.name for item in translations if item.locale == locale.value),
                None,
            ),
            translations=translations,
            created_at=category.created_at,
            updated_at=category.updated_at,
            created_by=category.created_by,
            updated_by=category.updated_by,
        )

    async def list_all(
        self, locale: CategoryLocaleVO
    ) -> tuple[CategoryListItemDTO, ...]:
        content = aliased(CategoryContentModel)
        rows = (
            await self._session.execute(
                select(CategoryModel.id, CategoryModel.parent_id, content.name)
                .outerjoin(
                    content,
                    (content.category_id == CategoryModel.id)
                    & (content.locale_code == locale.value),
                )
                .order_by(
                    CategoryModel.parent_id.nullsfirst(),
                    content.name.nullsfirst(),
                    CategoryModel.id,
                )
            )
        ).all()
        return tuple(
            CategoryListItemDTO(row.id, row.parent_id, row.name) for row in rows
        )
