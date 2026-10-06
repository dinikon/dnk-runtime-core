from dataclasses import dataclass

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)


@dataclass(frozen=True, slots=True)
class GetContentBlockQuery:
    block_id: ContentBlockIdVO
