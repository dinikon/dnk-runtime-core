from dataclasses import replace

from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.application.product.query.get_product.dto import (
    ProductDetailsDTO,
    ProductVariantDTO,
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
        variants = details.variants or (
            ProductVariantDTO(details.variant_id, details.sku_id, None, (), None),
        )
        codes = (
            await self._skus.get_codes(tuple(item.sku_id for item in variants))
            if len(variants) > 1
            else {variants[0].sku_id: await self._skus.get_code(variants[0].sku_id)}
        )
        resolved = []
        for variant in variants:
            code = codes.get(variant.sku_id)
            if code is None:
                raise ProductSkuNotFoundError("SKU not found.")
            resolved.append(replace(variant, sku_code=code))
        return replace(details, sku_code=resolved[0].sku_code, variants=tuple(resolved))
