from dataclasses import dataclass

from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class DeleteProductTypeCommand:
    type_id: ProductTypeIdVO
