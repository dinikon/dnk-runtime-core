from dataclasses import dataclass

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)


@dataclass(frozen=True, slots=True)
class DeleteContentBlockCommand:
    block_id: ContentBlockIdVO
