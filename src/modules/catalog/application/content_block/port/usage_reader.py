from typing import Protocol

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)


class ContentBlockUsageReaderPort(Protocol):
    async def is_in_use(self, block_id: ContentBlockIdVO) -> bool: ...
