from dataclasses import dataclass
from uuid import UUID

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockType,
)


@dataclass(frozen=True, slots=True)
class CreateContentBlockResultDTO:
    id: UUID
    code: str
    type: ContentBlockType
    is_system: bool
    translations: dict[str, str]
