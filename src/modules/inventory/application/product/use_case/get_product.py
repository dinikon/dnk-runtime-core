from typing import Protocol

from src.modules.inventory.application.product.dto import ProductDTO
from src.modules.inventory.application.product.query.get_product_query import (
    GetProductQuery,
)
from src.modules.inventory.application.product.query.repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.inventory.domain.product.error import ProductNotFoundError


class GetProductUseCaseProtocol(Protocol):
    """Порт use case получения одного товара."""

    async def __call__(self, query: GetProductQuery) -> ProductDTO:
        """Возвращает товар tenant или поднимает not-found ошибку."""
        ...


class GetProductUseCase:
    """Use case чтения одного товара через query repository."""

    def __init__(self, query_repository: ProductQueryRepositoryProtocol):
        """Инициализирует use case query-репозиторием товаров."""
        self._query_repository = query_repository

    async def __call__(self, query: GetProductQuery) -> ProductDTO:
        """Выполняет query получения товара и проверяет not-found сценарий."""
        product = await self._query_repository.get_by_id(
            tenant_id=query.tenant_id,
            product_id=query.product_id,
        )
        if product is None:
            raise ProductNotFoundError(str(query.product_id))
        return product
