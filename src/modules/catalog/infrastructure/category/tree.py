from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.error import CategoryNotFoundError
from src.modules.catalog.domain.error import CatalogConflictError
from src.modules.catalog.infrastructure.persistence.models.category import CategoryModel


class SqlAlchemyCategoryTree:
    """Читает immutable снимок предков под lock сценария."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает ту же tenant-сессию, что и write repository."""
        self._session = session

    async def ancestors(
        self, parent_id: CategoryIdVO | None
    ) -> frozenset[CategoryIdVO]:
        """Проверяет наличие цепочки и сообщает о повреждённом SQL-дереве."""
        visited: set[CategoryIdVO] = set()
        current = parent_id
        while current is not None:
            if current in visited:
                raise CatalogConflictError("Существующее дерево содержит цикл.")
            row = (
                await self._session.execute(
                    select(CategoryModel.parent_id).where(
                        CategoryModel.id == current.uuid
                    )
                )
            ).one_or_none()
            if row is None:
                raise CategoryNotFoundError("Родительская категория отсутствует.")
            visited.add(current)
            current = None if row[0] is None else CategoryIdVO(row[0])
        return frozenset(visited)
