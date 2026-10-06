from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.application.product.query.get_variant.dto import (
    GetVariantResultDTO,
)
from src.modules.catalog.application.product.query.get_variant.query import (
    GetVariantQuery,
)
from src.modules.catalog.domain.product.error import (
    ProductNotFoundError,
    ProductSkuNotFoundError,
)


class GetVariantHandler:
    def __init__(
        self, repository: ProductQueryRepositoryProtocol, skus: SkuReaderPort
    ) -> None:
        self._repository, self._skus = repository, skus

    async def execute(self, query: GetVariantQuery) -> GetVariantResultDTO:
        details = await self._repository.get_details(query.product_id, query.locale)
        if details is None:
            raise ProductNotFoundError("Product not found.")
        variant = next(
            (item for item in details.variants if item.id == query.variant_id.uuid),
            None,
        )
        if variant is None:
            raise ProductNotFoundError("Variant not found in product.")
        code = await self._skus.get_code(variant.sku_id)
        if code is None:
            raise ProductSkuNotFoundError("SKU not found.")
        return GetVariantResultDTO(
            variant.id,
            details.id,
            variant.sku_id,
            code,
            query.locale.value,
            variant.content_locales,
            variant.short_description,
        )
