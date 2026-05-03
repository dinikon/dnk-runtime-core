from typing import Protocol

from src.modules.inventory.application.product.dto import ProductDTO
from src.modules.inventory.application.product.query.list_products_query import (
    ListProductsQuery,
)
from src.modules.inventory.application.product.query.repository import (
    ProductQueryRepositoryProtocol,
)


class ListProductsUseCaseProtocol(Protocol):
    """Порт use case получения списка товаров."""

    async def __call__(self, query: ListProductsQuery) -> list[ProductDTO]:
        """Возвращает страницу товаров tenant."""
        ...


class ListProductsUseCase:
    """Use case чтения списка товаров через query repository."""

    def __init__(self, query_repository: ProductQueryRepositoryProtocol):
        """Инициализирует use case query-репозиторием товаров."""
        self._query_repository = query_repository

    async def __call__(self, query: ListProductsQuery) -> list[ProductDTO]:
        """Выполняет query списка товаров."""
        return await self._query_repository.list(
            tenant_id=query.tenant_id,
            limit=query.limit,
            offset=query.offset,
            category_id=query.category_id,
        )
