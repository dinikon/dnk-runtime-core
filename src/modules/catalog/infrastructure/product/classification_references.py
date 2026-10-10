from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.domain.category.error import CategoryNotFoundError
from src.modules.catalog.domain.tag.error import TagNotFoundError
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel
from src.modules.catalog.infrastructure.persistence.models.tag import TagModel


class SqlAlchemyClassificationReferences:
    """Читает только необходимые Product идентификаторы текущего tenant."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует общую сессию внешнего UoW."""
        self._session = session

    async def categories(
        self, identifiers: tuple[CategoryIdVO, ...]
    ) -> frozenset[CategoryIdVO]:
        """Проверяет существование явно назначаемых категорий."""
        ids = frozenset(
            CategoryIdVO(i)
            for i in (
                await self._session.scalars(
                    select(CategoryModel.id).where(
                        CategoryModel.id.in_([i.uuid for i in identifiers])
                    )
                )
            ).all()
        )
        if set(identifiers) - ids:
            raise CategoryNotFoundError("Назначаемая категория отсутствует.")
        return ids

    async def tags(self, identifiers: tuple[TagIdVO, ...]) -> frozenset[TagIdVO]:
        """Проверяет существование явно назначаемых меток."""
        ids = frozenset(
            TagIdVO(i)
            for i in (
                await self._session.scalars(
                    select(TagModel.id).where(
                        TagModel.id.in_([i.uuid for i in identifiers])
                    )
                )
            ).all()
        )
        if set(identifiers) - ids:
            raise TagNotFoundError("Назначаемая метка отсутствует.")
        return ids
