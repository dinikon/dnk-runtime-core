from typing import Protocol
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO


class CategoryTreePort(Protocol):
    """Минимальное чтение предков без загрузки чужих агрегатов."""

    async def ancestors(
        self, parent_id: CategoryIdVO | None
    ) -> frozenset[CategoryIdVO]:
        """Проверяет родителя и возвращает его самого и всех предков."""
        ...
