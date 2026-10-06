from dataclasses import dataclass
from uuid import UUID
from src.modules.catalog.application.product.query.get_product.dto import (
    ProductContentDTO,
)


@dataclass(frozen=True, slots=True)
class GetVariantResultDTO:
    id: UUID
    product_id: UUID
    sku_id: UUID
    sku_code: str
    requested_locale: str
    content_locales: tuple[str, ...]
    content: ProductContentDTO | None
