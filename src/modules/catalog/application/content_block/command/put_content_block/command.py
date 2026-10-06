from dataclasses import dataclass

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
    ContentBlockType,
)


@dataclass(frozen=True, slots=True)
class PutContentBlockCommand:
    block_id: ContentBlockIdVO
    type: ContentBlockType
    translations: dict[str, str]
