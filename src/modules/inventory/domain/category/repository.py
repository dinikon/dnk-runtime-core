from typing import Protocol

from src.modules.inventory.domain.category.entity import CategoryEntity
from src.modules.inventory.domain.category.value_object import CategoryIdVO
from src.modules.shared import EntityIdVO


class CategoryCommandRepositoryProtocol(Protocol):
    """Порт командного хранения категорий товаров."""

    async def load(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> CategoryEntity | None:
        """Загружает категорию tenant по id или возвращает None."""
        ...

    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        category: CategoryEntity,
    ) -> CategoryEntity:
        """Сохраняет категорию tenant и возвращает актуальную entity."""
        ...

    async def delete(
        self,
        *,
        tenant_id: EntityIdVO,
        category_id: CategoryIdVO,
    ) -> None:
        """Удаляет категорию tenant по id."""
        ...
