from typing import Protocol

from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)


class ContentBlockRepositoryProtocol(Protocol):
    """Хранение корня ContentBlockDefinition в текущей tenant-транзакции."""

    async def add(self, block: ContentBlockDefinition) -> None: ...

    async def get_for_update(
        self, block_id: ContentBlockIdVO
    ) -> ContentBlockDefinition | None: ...

    async def save(self, block: ContentBlockDefinition) -> None: ...

    async def delete(self, block: ContentBlockDefinition) -> None: ...
