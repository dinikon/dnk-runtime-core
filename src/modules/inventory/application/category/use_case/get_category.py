from typing import Protocol

from src.modules.inventory.application.category.dto import CategoryDTO
from src.modules.inventory.application.category.query.get_category_query import (
    GetCategoryQuery,
)
from src.modules.inventory.application.category.query.repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.inventory.domain.category.error import CategoryNotFoundError


class GetCategoryUseCaseProtocol(Protocol):
    """Порт use case получения одной категории."""

    async def __call__(self, query: GetCategoryQuery) -> CategoryDTO:
        """Возвращает категорию tenant или поднимает not-found ошибку."""
        ...


class GetCategoryUseCase:
    """Use case чтения одной категории через query repository."""

    def __init__(self, query_repository: CategoryQueryRepositoryProtocol):
        """Инициализирует use case query-репозиторием категорий."""
        self._query_repository = query_repository

    async def __call__(self, query: GetCategoryQuery) -> CategoryDTO:
        """Выполняет query получения категории и проверяет not-found сценарий."""
        category = await self._query_repository.get_by_id(
            tenant_id=query.tenant_id,
            category_id=query.category_id,
        )
        if category is None:
            raise CategoryNotFoundError(str(query.category_id))
        return category
