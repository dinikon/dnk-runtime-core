from dataclasses import replace

from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.application.product.query.get_product.dto import (
    ProductDetailsDTO,
    VariableProductDetailsDTO,
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

    async def execute(
        self, query: GetProductQuery
    ) -> ProductDetailsDTO | VariableProductDetailsDTO:
        details = await self._repository.get_details(query.product_id, query.locale)
        if details is None:
            raise ProductNotFoundError("Product not found.")
        if isinstance(details, ProductDetailsDTO):
            sku_code = await self._skus.get_code(details.sku_id)
            if sku_code is None:
                raise ProductSkuNotFoundError("SKU not found.")
            return replace(details, sku_code=sku_code)
        sku_codes = {}
        for variant in details.variants:
            if variant.sku_id not in sku_codes:
                sku_code = await self._skus.get_code(variant.sku_id)
                if sku_code is None:
                    raise ProductSkuNotFoundError("SKU not found.")
                sku_codes[variant.sku_id] = sku_code
        return replace(
            details,
            variants=tuple(
                replace(variant, sku_code=sku_codes[variant.sku_id])
                for variant in details.variants
            ),
        )
