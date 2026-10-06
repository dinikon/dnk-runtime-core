from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.catalog.application.product.query.list_products.dto import (
    ProductListItemDTO,
)
from src.modules.catalog.application.product.query.list_products.query import (
    ListProductsQuery,
)


class ListProductsHandler:
    def __init__(self, repository: ProductQueryRepositoryProtocol) -> None:
        self._repository = repository

    async def execute(self, query: ListProductsQuery) -> tuple[ProductListItemDTO, ...]:
        return await self._repository.list_products(query.locale)
