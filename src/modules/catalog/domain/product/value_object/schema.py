from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)
from dataclasses import dataclass
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope


@dataclass(frozen=True, slots=True)
class ContentBlockSnapshot:
    """Данные блока, необходимые для проверки контента Product."""

    block_id: ContentBlockIdVO
    value_type: ContentValueType
    scope: ContentScope
    required: bool
    position: int


@dataclass(frozen=True, slots=True)
class ProductSchemaSnapshot:
    """Согласованный неизменяемый снимок схемы; не чужой агрегат."""

    product_type_id: ProductTypeIdVO
    version: int
    blocks: tuple[ContentBlockSnapshot, ...]
