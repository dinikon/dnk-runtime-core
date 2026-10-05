from dataclasses import replace

from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.application.product.query.get_product.dto import (
    ProductDetailsDTO,
)
from src.modules.catalog.application.product.query.get_product.query import (
    GetProductQuery,
)
from src.modules.catalog.domain.product.error import (
    ProductNotFoundError,
    ProductSkuNotFoundError,
)


class GetProductHandler:
    def __init__(
        self, repository: ProductQueryRepositoryProtocol, skus: SkuReaderPort
    ) -> None:
        self._repository = repository
        self._skus = skus

    async def execute(self, query: GetProductQuery) -> ProductDetailsDTO:
        details = await self._repository.get_details(query.product_id, query.locale)
        if details is None:
            raise ProductNotFoundError("Product not found.")
        sku_code = await self._skus.get_code(details.sku_id)
        if sku_code is None:
            raise ProductSkuNotFoundError("SKU not found.")
        return replace(details, sku_code=sku_code)
