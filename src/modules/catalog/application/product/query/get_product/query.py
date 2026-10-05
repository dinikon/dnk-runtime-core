from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


@dataclass(frozen=True, slots=True)
class GetProductQuery:
    product_id: ProductIdVO
    locale: ProductLocaleVO
