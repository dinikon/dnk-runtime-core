from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel
from src.modules.catalog.infrastructure.persistence.models.tag import TagModel


class SqlAlchemyClassificationReferences:
    """Проверяет существующие связи в том же UoW, что CatalogItem."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает tenant session внешнего UoW."""
        self._session = session

    async def categories(
        self, identifiers: tuple[CategoryIdVO, ...]
    ) -> frozenset[CategoryIdVO]:
        """Возвращает существующие Category ID из одного SELECT."""
        rows = await self._session.scalars(
            select(CategoryModel.id).where(
                CategoryModel.id.in_(tuple(i.uuid for i in identifiers))
            )
        )
        return frozenset(CategoryIdVO(i) for i in rows)

    async def tags(self, identifiers: tuple[TagIdVO, ...]) -> frozenset[TagIdVO]:
        """Возвращает существующие Tag ID из одного SELECT."""
        rows = await self._session.scalars(
            select(TagModel.id).where(
                TagModel.id.in_(tuple(i.uuid for i in identifiers))
            )
        )
        return frozenset(TagIdVO(i) for i in rows)
