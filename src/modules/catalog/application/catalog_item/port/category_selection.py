from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from typing import Protocol
from src.modules.catalog.domain.catalog_item.value_object.categories import (
    CatalogItemCategoriesVO,
)

from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)


class CatalogCategorySelectionPort(Protocol):
    """Разрешает назначение в текущем tenant, удерживая ссылки до конца UoW."""

    async def default_id(self, tenant_id: EntityIdVO) -> CatalogCategoryIdVO:
        """Читает ссылку tenant для новых карточек."""
        ...

    async def ensure_exist(
        self, tenant_id: EntityIdVO, selection: CatalogItemCategoriesVO
    ) -> None:
        """Проверяет наличие всех выбранных категорий под блокировкой дерева."""
        ...
