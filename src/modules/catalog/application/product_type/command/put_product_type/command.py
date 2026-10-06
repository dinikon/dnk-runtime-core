from dataclasses import dataclass

from src.modules.catalog.domain.product_type.aggregate import ProductTypeContentBlock
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)


@dataclass(frozen=True, slots=True)
class PutProductTypeCommand:
    type_id: ProductTypeIdVO
    translations: dict[str, str]
    blocks: tuple[ProductTypeContentBlock, ...]
    expected_schema_version: int
