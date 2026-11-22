from src.modules.catalog.application.catalog_category.query.list_catalog_categories.repository import (
    CatalogCategoryQueryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_category.query.list_catalog_categories.query import (
    ListCatalogCategoriesQuery,
)
from src.modules.catalog.application.catalog_category.query.list_catalog_categories.dto import (
    ListCatalogCategoriesResultDTO,
)


class ListCatalogCategoriesHandler:
    """Получает дерево для выбранного языка."""

    def __init__(self, repository: CatalogCategoryQueryRepositoryProtocol) -> None:
        """Принимает зависимости текущего сценария."""
        self.repository = repository

    async def execute(
        self, query: ListCatalogCategoriesQuery
    ) -> ListCatalogCategoriesResultDTO:
        """Возвращает дерево с названиями для выбранной локали."""
        return await self.repository.list_tree(query.locale)
