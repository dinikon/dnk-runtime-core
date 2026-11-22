from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Protocol
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.catalog_category.aggregate import CatalogCategory


class CatalogCategoryRepositoryProtocol(Protocol):
    """Запись дерева сериализуется в пределах tenant и текущей транзакции."""

    async def lock_tree(self, tenant_id: EntityIdVO) -> None:
        """Сериализует изменения дерева до конца транзакции."""
        ...

    async def parents(self) -> dict[CatalogCategoryIdVO, CatalogCategoryIdVO | None]:
        """Читает связи с родителями для проверки переноса ветки."""
        ...

    async def get(self, identifier: CatalogCategoryIdVO) -> CatalogCategory:
        """Загружает категорию и её переводы по идентификатору."""
        ...

    async def add(self, category: CatalogCategory) -> None:
        """Записывает новый узел вместе с исходным названием."""
        ...

    async def save(self, category: CatalogCategory) -> None:
        """Сохраняет изменённое положение и переводы категории."""
        ...

    async def has_items(self, identifier: CatalogCategoryIdVO) -> bool:
        """Проверяет использование в основных и дополнительных назначениях."""
        ...

    async def set_default(self, identifier: CatalogCategoryIdVO) -> None:
        """Меняет ссылку для создаваемых карточек."""
        ...

    async def delete(self, category: CatalogCategory) -> None:
        """Удаляет проверенную категорию с её переводами."""
        ...
