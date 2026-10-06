from dataclasses import dataclass

from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO


@dataclass(frozen=True, slots=True)
class DeleteProductCommand:
    product_id: ProductIdVO
