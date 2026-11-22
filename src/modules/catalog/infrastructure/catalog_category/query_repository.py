from sqlalchemy import and_, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.catalog_category import (
    CatalogCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_category_translation import (
    CatalogCategoryTranslationModel,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.application.catalog_category.query.list_catalog_categories.dto import (
    CatalogCategoryRowDTO,
    ListCatalogCategoriesResultDTO,
)


class SqlAlchemyCatalogCategoryQueryRepository:
    """Читает локализованные названия и связи дерева одним запросом."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает зависимости текущего сценария."""
        self.session = session

    async def list_tree(self, locale: LocaleVO) -> ListCatalogCategoriesResultDTO:
        """Возвращает запрошенный перевод и резервное название по первой локали."""
        nodes = CatalogCategoryModel.__table__
        names = CatalogCategoryTranslationModel.__table__
        fallback = (
            select(names.c.locale, names.c.name)
            .where(names.c.category_id == nodes.c.id)
            .order_by(names.c.locale)
            .limit(1)
            .correlate(nodes)
            .lateral("fallback")
        )
        query = (
            select(
                nodes.c.id,
                nodes.c.parent_id,
                names.c.name,
                fallback.c.locale.label("fallback_locale"),
                fallback.c.name.label("fallback_name"),
                nodes.c.is_default,
            )
            .select_from(
                nodes.join(fallback, true()).outerjoin(
                    names,
                    and_(
                        names.c.category_id == nodes.c.id,
                        names.c.locale == locale.value,
                    ),
                )
            )
            .order_by(names.c.name, nodes.c.id)
        )
        return ListCatalogCategoriesResultDTO(
            tuple(
                CatalogCategoryRowDTO(**row)
                for row in (await self.session.execute(query)).mappings()
            )
        )
