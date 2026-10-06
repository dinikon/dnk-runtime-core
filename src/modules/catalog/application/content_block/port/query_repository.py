from typing import Protocol

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    ContentBlockDetailsDTO,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ContentBlockListItemDTO,
)


class ContentBlockQueryRepositoryProtocol(Protocol):
    """Проекции определений контент-блоков без восстановления агрегатов."""

    async def get(
        self, block_id: ContentBlockIdVO
    ) -> ContentBlockDetailsDTO | None: ...

    async def list(self) -> tuple[ContentBlockListItemDTO, ...]: ...
