from typing import Protocol
from src.modules.catalog.application.catalog_category.query.list_catalog_categories.dto import (
    ListCatalogCategoriesResultDTO,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO


class CatalogCategoryQueryRepositoryProtocol(Protocol):
    """Порт чтения локализованного дерева."""

    async def list_tree(self, locale: LocaleVO) -> ListCatalogCategoriesResultDTO:
        """Возвращает связи дерева и названия для выбранного языка."""
        ...
