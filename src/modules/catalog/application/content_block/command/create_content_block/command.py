from dataclasses import dataclass

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)


@dataclass(frozen=True, slots=True)
class CreateContentBlockCommand:
    code: str
    type: ContentBlockType
    translations: dict[str, str]
