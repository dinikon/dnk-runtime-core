from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.locale import ProductLocaleVO


@dataclass(frozen=True, slots=True)
class ListProductsQuery:
    locale: ProductLocaleVO
