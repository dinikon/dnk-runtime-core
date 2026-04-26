from typing import Protocol

from src.modules.inventory.application.category.dto import CategoryDTO
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.shared import EntityIdVO


class CategoryQueryRepositoryProtocol(Protocol):
    """Порт чтения категорий товаров для inventory query use cases."""

    async def get_by_id(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> CategoryDTO | None:
        """Возвращает категорию tenant по id или None."""
        ...

    async def list(
        self,
        *,
        tenant_id: EntityIdVO,
        limit: int,
        offset: int,
        parent_category_id: CategoryIdVO | None = None,
    ) -> list[CategoryDTO]:
        """Возвращает страницу категорий tenant."""
        ...


__all__ = ["CategoryQueryRepositoryProtocol"]
