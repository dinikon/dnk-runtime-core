from src.modules.catalog.application.category.port.query_repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.catalog.application.category.query.list_categories.dto import (
    CategoryListItemDTO,
)
from src.modules.catalog.application.category.query.list_categories.query import (
    ListCategoriesQuery,
)


class ListCategoriesHandler:
    def __init__(self, repository: CategoryQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(
        self, query: ListCategoriesQuery
    ) -> tuple[CategoryListItemDTO, ...]:
        return await self._repository.list_all(query.locale)
