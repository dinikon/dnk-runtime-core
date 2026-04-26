from typing import Protocol

from src.modules.inventory.application.category.dto import CategoryDTO
from src.modules.inventory.application.category.query.list_categories_query import (
    ListCategoriesQuery,
)
from src.modules.inventory.application.category.query.repository import (
    CategoryQueryRepositoryProtocol,
)


class ListCategoriesUseCaseProtocol(Protocol):
    """Порт use case получения списка категорий."""

    async def __call__(self, query: ListCategoriesQuery) -> list[CategoryDTO]:
        """Возвращает страницу категорий tenant."""
        ...


class ListCategoriesUseCase:
    """Use case чтения списка категорий через query repository."""

    def __init__(self, query_repository: CategoryQueryRepositoryProtocol):
        """Инициализирует use case query-репозиторием категорий."""
        self._query_repository = query_repository

    async def __call__(self, query: ListCategoriesQuery) -> list[CategoryDTO]:
        """Выполняет query списка категорий."""
        return await self._query_repository.list(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
            parent_category_id=query.parent_category_id,
        )
