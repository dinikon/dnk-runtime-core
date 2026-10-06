from typing import Protocol

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product_type.aggregate import ContentScope
from src.modules.catalog.domain.product_type.value_object.product_type_id import (
    ProductTypeIdVO,
)


class ProductTypeUsageReaderPort(Protocol):
    async def type_in_use(self, type_id: ProductTypeIdVO) -> bool: ...

    async def content_block_in_use(
        self, type_id: ProductTypeIdVO, scope: ContentScope, block_id: ContentBlockIdVO
    ) -> bool: ...

    async def missing_required_value(
        self, type_id: ProductTypeIdVO, scope: ContentScope, block_id: ContentBlockIdVO
    ) -> bool: ...
