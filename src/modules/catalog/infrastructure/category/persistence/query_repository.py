from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.application.category.query.get_category.dto import (
    GetCategoryDetailsDTO,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    ListCategoriesPageDTO,
)
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel
from src.modules.catalog.infrastructure.persistence.models.category_translation import (
    CategoryTranslationModel,
)
from src.modules.catalog.infrastructure.category.persistence.query_mapper import (
    CategoryQueryMapper,
)
from sqlalchemy.sql import Select


class SqlAlchemyCategoryQueryRepository:
    """Читает отдельные проекции справочника без восстановления агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает tenant-сессию общей транзакции."""
        self._session = session

    @staticmethod
    def _statement() -> Select:
        """Готовит техническую проекцию с числом дочерних узлов."""
        statement = select(CategoryModel.__table__)
        children = CategoryModel.__table__.alias("children")
        statement = statement.add_columns(
            select(func.count())
            .select_from(children)
            .where(children.c.parent_id == CategoryModel.id)
            .correlate(CategoryModel.__table__)
            .scalar_subquery()
            .label("child_count")
        )
        return statement

    async def get_details(
        self, identifier: CategoryIdVO, locale: str
    ) -> GetCategoryDetailsDTO | None:
        """Возвращает детали и явные локали либо отсутствие объекта."""
        row = (
            (
                await self._session.execute(
                    self._statement().where(CategoryModel.id == identifier.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        labels = dict(
            (
                await self._session.execute(
                    select(
                        CategoryTranslationModel.locale, CategoryTranslationModel.label
                    ).where(CategoryTranslationModel.category_id == identifier.uuid)
                )
            ).all()
        )
        return CategoryQueryMapper.to_details(row, labels, locale)

    async def list_page(
        self,
        locale: str,
        search: str,
        page: int,
        page_size: int,
        parent_id: CategoryIdVO | None,
        roots_only: bool,
    ) -> ListCategoriesPageDTO:
        """Считает корни до пагинации с явным фильтром ветви и locale."""
        statement = (
            self._statement()
            .add_columns(CategoryTranslationModel.label)
            .outerjoin(
                CategoryTranslationModel,
                (CategoryTranslationModel.category_id == CategoryModel.id)
                & (CategoryTranslationModel.locale == locale),
            )
        )
        if parent_id is not None:
            statement = statement.where(CategoryModel.parent_id == parent_id.uuid)
        elif roots_only:
            statement = statement.where(CategoryModel.parent_id.is_(None))
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            statement = statement.where(
                or_(
                    CategoryTranslationModel.label.ilike(
                        "%" + escaped + "%", escape="\\"
                    ),
                    cast(CategoryModel.id, String).ilike(
                        "%" + escaped + "%", escape="\\"
                    ),
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(CategoryModel.created_at, CategoryModel.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .mappings()
            .all()
        )
        return ListCategoriesPageDTO(
            tuple(CategoryQueryMapper.to_list_item(r) for r in rows),
            total or 0,
            page,
            page_size,
        )
