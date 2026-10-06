from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


@dataclass(frozen=True, slots=True)
class GetVariantQuery:
    product_id: ProductIdVO
    variant_id: VariantIdVO
    locale: ProductLocaleVO
