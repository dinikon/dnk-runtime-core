from src.modules.catalog.application.category.port.query_repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.catalog.application.category.query.get_category.dto import (
    CategoryDetailsDTO,
)
from src.modules.catalog.application.category.query.get_category.query import (
    GetCategoryQuery,
)
from src.modules.catalog.domain.category.error import CategoryNotFoundError


class GetCategoryHandler:
    def __init__(self, repository: CategoryQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: GetCategoryQuery) -> CategoryDetailsDTO:
        result = await self._repository.get_details(query.category_id, query.locale)
        if result is None:
            raise CategoryNotFoundError("Category not found.")
        return result
