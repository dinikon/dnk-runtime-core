from collections.abc import Mapping
from src.modules.catalog.domain.catalog_category.aggregate import CatalogCategory
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_category import (
    CatalogCategoryModel,
)


class CatalogCategoryMapper:
    """Собирает узел дерева из строки категории и названий без I/O."""

    @staticmethod
    def to_domain(
        row: CatalogCategoryModel, names: Mapping[str, str]
    ) -> CatalogCategory:
        """Восстанавливает агрегат через фабрику с названиями и родителем."""
        return CatalogCategory.restore(
            CatalogCategoryIdVO(row.id),
            CatalogCategoryIdVO(row.parent_id) if row.parent_id else None,
            names,
            is_default=row.is_default,
        )
